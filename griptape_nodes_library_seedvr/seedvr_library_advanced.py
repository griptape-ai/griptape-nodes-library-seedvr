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
        self._add_submodule_to_path(submodule_path)

    def after_library_nodes_loaded(self, library_data: LibrarySchema, library: Library) -> None:
        logger.info(f"Finished loading '{library_data.name}' library")

    def _get_library_root(self) -> Path:
        return Path(__file__).parent

    def _init_submodule(self) -> Path:
        library_root = self._get_library_root()
        submodule_dir = library_root / "seedvr"
        if submodule_dir.exists() and any(submodule_dir.iterdir()):
            return submodule_dir
        subprocess.check_call(["git", "-C", str(library_root.parent), "submodule", "update", "--init", "--recursive"])
        if not submodule_dir.exists() or not any(submodule_dir.iterdir()):
            raise RuntimeError(f"Submodule init failed: {submodule_dir}")
        logger.info("Submodule initialized")
        return submodule_dir

    def _add_submodule_to_path(self, submodule_path: Path) -> None:
        if str(submodule_path) not in sys.path:
            sys.path.insert(0, str(submodule_path))
        logger.info(f"Added {submodule_path} to sys.path")
