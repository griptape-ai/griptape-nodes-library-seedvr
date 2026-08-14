import logging
import subprocess
import sys
from pathlib import Path

from griptape_nodes.node_library.advanced_node_library import AdvancedNodeLibrary
from griptape_nodes.node_library.library_registry import Library, LibrarySchema

logger = logging.getLogger("seedvr_library")


class SeedVRLibraryAdvanced(AdvancedNodeLibrary):
    def before_library_nodes_loaded(self, library_data: LibrarySchema, library: Library) -> None:
        logger.info(f"Loading '{library_data.name}' library...")
        submodule_path = self._init_submodule()
        if not self._is_installed(submodule_path):
            self._install_from_requirements(submodule_path)
            self._apply_patches()
            self._write_installed_sentinel(submodule_path)
        # Always re-apply sys.path — it does not persist across engine restarts,
        # and _install_package is idempotent (no-ops if path already present).
        self._install_package(submodule_path)

    def after_library_nodes_loaded(self, library_data: LibrarySchema, library: Library) -> None:
        logger.info(f"Finished loading '{library_data.name}' library")

    def _get_library_root(self) -> Path:
        return Path(__file__).parent

    def _get_venv_python_path(self) -> Path:
        root = self._get_library_root()
        if sys.platform == "win32":
            return root / ".venv" / "Scripts" / "python.exe"
        return root / ".venv" / "bin" / "python"

    def _init_submodule(self) -> Path:
        library_root = self._get_library_root()
        submodule_dir = library_root / "seedvr"
        if submodule_dir.exists() and any(submodule_dir.iterdir()):
            logger.info("Submodule already initialized")
            return submodule_dir
        subprocess.check_call(
            ["git", "-C", str(library_root.parent), "submodule", "update", "--init", "--recursive"]
        )
        if not submodule_dir.exists() or not any(submodule_dir.iterdir()):
            raise RuntimeError(f"Submodule init failed: {submodule_dir}")
        logger.info("Submodule initialized successfully")
        return submodule_dir

    def _ensure_pip(self) -> None:
        venv_python = self._get_venv_python_path()
        result = subprocess.run([str(venv_python), "-m", "pip", "--version"], capture_output=True)
        if result.returncode == 0:
            return
        subprocess.check_call([str(venv_python), "-m", "ensurepip", "--upgrade"])

    def _get_submodule_commit(self, submodule_path: Path) -> str:
        """Return the HEAD commit SHA of the submodule (the version pinned by the library author)."""
        return subprocess.check_output(
            ["git", "-C", str(submodule_path), "rev-parse", "HEAD"], text=True
        ).strip()

    def _get_installed_sentinel(self) -> Path:
        return self._get_library_root() / ".installed_commit"

    def _write_installed_sentinel(self, submodule_path: Path) -> None:
        self._get_installed_sentinel().write_text(self._get_submodule_commit(submodule_path))

    def _is_installed(self, submodule_path: Path) -> bool:
        """For sys.path installs, the commit sentinel is the only durable install signal.

        sys.path mutations do not survive across engine restarts and cannot be observed
        from a venv subprocess, so we rely entirely on the committed-version sentinel.
        """
        sentinel = self._get_installed_sentinel()
        if not sentinel.exists():
            return False
        return sentinel.read_text().strip() == self._get_submodule_commit(submodule_path)

    def _install_from_requirements(self, submodule_path: Path) -> None:
        """Install dependencies from the submodule's requirements.txt.

        Uses --no-build-isolation so that packages requiring torch at build time
        (e.g., flash-attn) can find the torch already installed in the venv.
        """
        requirements_file = submodule_path / "requirements.txt"
        if not requirements_file.exists():
            logger.info("No requirements.txt found in submodule, skipping")
            return
        venv_python = self._get_venv_python_path()
        self._ensure_pip()
        logger.info(f"Installing requirements from {requirements_file}...")
        subprocess.check_call(
            [str(venv_python), "-m", "pip", "install", "--no-build-isolation", "-r", str(requirements_file)]
        )
        logger.info("Requirements installed successfully")

    def _install_package(self, submodule_path: Path) -> None:
        """Add the submodule root to sys.path so its modules are importable."""
        import_root = submodule_path
        if str(import_root) not in sys.path:
            sys.path.insert(0, str(import_root))
        logger.info(f"Added {import_root} to sys.path")

    def _apply_patches(self) -> None:
        """Install supplemental packages not in requirements.txt.

        flash_attn: requires torch pre-installed; must use --no-build-isolation.
        apex: not on PyPI; download pre-built wheel from the HuggingFace model repo
              and install. Detects Python/CUDA version automatically.
        """
        venv_python = self._get_venv_python_path()

        # --- flash_attn ---
        result = subprocess.run(
            [str(venv_python), "-c", "import flash_attn"],
            capture_output=True,
        )
        if result.returncode != 0:
            logger.info("Installing flash_attn==2.5.9.post1 (requires --no-build-isolation)...")
            subprocess.check_call(
                [
                    str(venv_python),
                    "-m",
                    "pip",
                    "install",
                    "--no-build-isolation",
                    "flash_attn==2.5.9.post1",
                ]
            )
            logger.info("flash_attn installed successfully")
        else:
            logger.info("flash_attn already installed, skipping")

        # --- NVIDIA apex ---
        result = subprocess.run(
            [str(venv_python), "-c", "import apex"],
            capture_output=True,
        )
        if result.returncode != 0:
            self._install_apex(venv_python)
        else:
            logger.info("apex already installed, skipping")

    def _install_apex(self, venv_python: Path) -> None:
        """Download and install the pre-built apex wheel from HuggingFace."""
        import urllib.request

        py_version = subprocess.check_output(
            [str(venv_python), "-c", "import sys; print(f'{sys.version_info.major}{sys.version_info.minor}')"],
            text=True,
        ).strip()

        # Pre-built wheels available from ByteDance-Seed/SeedVR2-3B:
        #   cp310 + torch 2.4.0 + CUDA 12.1
        #   cp39  + torch 2.4.0 + CUDA 12.4
        whl_map = {
            "310": "https://huggingface.co/ByteDance-Seed/SeedVR2-3B/resolve/main/apex-0.1-cp310-cp310-linux_x86_64.whl",
            "39": "https://huggingface.co/ByteDance-Seed/SeedVR2-3B/resolve/main/apex-0.1-cp39-cp39-linux_x86_64.whl",
        }

        whl_url = whl_map.get(py_version)
        if whl_url is None:
            logger.warning(
                f"No pre-built apex wheel available for Python {py_version}. "
                "Apex is optional — inference may work without it on some configurations."
            )
            return

        import tempfile

        logger.info(f"Downloading apex wheel for Python {py_version}...")
        with tempfile.NamedTemporaryFile(suffix=".whl", delete=False) as tmp:
            urllib.request.urlretrieve(whl_url, tmp.name)  # noqa: S310
            whl_path = tmp.name

        logger.info("Installing apex...")
        subprocess.check_call([str(venv_python), "-m", "pip", "install", whl_path])
        logger.info("apex installed successfully")
