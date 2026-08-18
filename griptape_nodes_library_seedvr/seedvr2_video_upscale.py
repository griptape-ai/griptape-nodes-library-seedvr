import datetime
import gc
import logging
import math
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

import torch
from einops import rearrange
from griptape.artifacts.video_url_artifact import VideoUrlArtifact
from griptape_nodes.exe_types.core_types import Parameter, ParameterMode
from griptape_nodes.exe_types.node_types import AsyncResult, SuccessFailureNode
from griptape_nodes.exe_types.param_components.project_file_parameter import ProjectFileParameter
from griptape_nodes.exe_types.param_components.seed_parameter import SeedParameter
from griptape_nodes.exe_types.param_types.parameter_button import ParameterButton
from griptape_nodes.exe_types.param_types.parameter_int import ParameterInt
from griptape_nodes.exe_types.param_types.parameter_video import ParameterVideo
from griptape_nodes.files.file import File
from griptape_nodes.traits.options import Options

logger = logging.getLogger(__name__)

MODEL_REPO_IDS = [
    "ByteDance-Seed/SeedVR2-3B",
    "ByteDance-Seed/SeedVR2-7B",
]

_MODEL_CONFIG: dict[str, tuple[str, str]] = {
    "ByteDance-Seed/SeedVR2-3B": ("configs_3b", "seedvr2_ema_3b.pth"),
    "ByteDance-Seed/SeedVR2-7B": ("configs_7b", "seedvr2_ema_7b.pth"),
}


def snap_to_4n1(n: int) -> int:
    """Snap n to the nearest valid 4n+1 value (1, 5, 9, 13, ...)."""
    if n <= 1:
        return 1
    return max(1, 4 * ((n - 1) // 4) + 1)


def ideal_batch_size(frame_count: int, max_batch_size: int = 21) -> int:
    """Compute the largest valid 4n+1 batch size that fits within the frame count."""
    ceiling = snap_to_4n1(max_batch_size)
    limit = min(frame_count, ceiling)
    return snap_to_4n1(limit)


def _make_windows(total: int, batch_size: int, step: int) -> list[tuple[int, int]]:
    """Split total frames into overlapping [start, end) windows."""
    if total <= batch_size:
        return [(0, total)]
    windows: list[tuple[int, int]] = []
    start = 0
    while start < total:
        end = min(start + batch_size, total)
        windows.append((start, end))
        if end >= total:
            break
        start += step
    return windows


def _compute_hann_weights(n: int, overlap: int, is_first: bool, is_last: bool) -> torch.Tensor:
    """Per-frame Hann blending weights for temporal overlap between batches.

    Frames inside the overlap zone at the start/end of a window fade in/out
    with a raised-cosine (Hann) curve so that adjacent windows sum to 1.0.
    """
    weights = torch.ones(n)
    if overlap <= 0 or n <= 1:
        return weights
    fade = min(overlap, n // 2)
    if not is_first:
        for i in range(fade):
            t = i / fade
            weights[i] = 0.5 - 0.5 * math.cos(math.pi * t)
    if not is_last:
        for i in range(fade):
            idx = n - 1 - i
            t = i / fade
            weights[idx] = min(weights[idx].item(), 0.5 - 0.5 * math.cos(math.pi * t))
    return weights


def _clear_vram() -> None:
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def _probe_video(video_path: str) -> tuple[float, int]:
    """Return (fps, frame_count) for a video file using ffprobe.

    Uses static_ffmpeg for a bundled cross-platform binary; falls back to a
    system ffprobe if static_ffmpeg is unavailable. Returns (0.0, 0) on failure.
    """
    import json
    import subprocess

    try:
        import static_ffmpeg.run

        _, ffprobe_bin = static_ffmpeg.run.get_or_fetch_platform_executables_else_raise()
    except Exception:
        ffprobe_bin = "ffprobe"

    try:
        result = subprocess.run(
            [
                ffprobe_bin,
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_streams",
                "-select_streams",
                "v:0",
                video_path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return 0.0, 0
        stream = json.loads(result.stdout).get("streams", [{}])[0]

        # fps — prefer avg_frame_rate, fall back to r_frame_rate
        fps = 0.0
        for key in ("avg_frame_rate", "r_frame_rate"):
            frac = stream.get(key, "0/0")
            if "/" in frac:
                num, den = frac.split("/")
                if float(den) > 0:
                    fps = float(num) / float(den)
                    if fps > 0:
                        break
            elif frac:
                fps = float(frac)
                if fps > 0:
                    break

        # frame count — use nb_frames if present, otherwise duration * fps
        nb_frames = int(stream.get("nb_frames") or 0)
        if nb_frames <= 0 and fps > 0:
            duration = float(stream.get("duration") or 0)
            nb_frames = int(duration * fps)

        return fps, nb_frames
    except Exception:
        return 0.0, 0


def _decode_video(video_path: str) -> tuple[list, float]:
    """Decode all frames from a video file. Returns (frames_rgb_list, fps).

    Tries cv2 first (fast, works for standard MP4/H.264). Falls back to
    PyAV+BytesIO for fragmented/CMAF MP4s that cv2 can't open.
    """
    import cv2

    frames: list = []
    raw_fps = 0.0

    cap = cv2.VideoCapture(video_path)
    if cap.isOpened():
        raw_fps = cap.get(cv2.CAP_PROP_FPS)
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        cap.release()

    if frames:
        return frames, raw_fps

    # cv2 failed (e.g. fragmented/CMAF MP4) — try PyAV via BytesIO which
    # supports arbitrary seeking and can find the moov atom anywhere in the file.
    logger.warning("cv2 could not read frames from %s — trying PyAV fallback", video_path)
    try:
        import io

        import av

        with open(video_path, "rb") as fh:
            buf = io.BytesIO(fh.read())
        container: Any = av.open(buf)
        video_stream = container.streams.video[0]
        avg_rate = video_stream.average_rate
        raw_fps = float(avg_rate) if avg_rate else 0.0
        for frame in container.decode(video=0):
            frames.append(frame.to_rgb().to_ndarray())
        container.close()
    except Exception as exc:
        logger.warning("PyAV fallback also failed: %s", exc)

    return frames, raw_fps


class SeedVR2VideoUpscale(SuccessFailureNode):
    """Upscale and restore video using SeedVR2 diffusion transformer from ByteDance."""

    _RUNNER_CACHE: dict[str, Any] = {}

    def __init__(self, name: str, metadata: dict[Any, Any] | None = None) -> None:
        super().__init__(name, metadata)

        # SeedParameter FIRST — must exist before any add_parameter calls because
        # after_value_set can fire during parameter initialization.
        self._seed_param = SeedParameter(self)

        self.add_parameter(
            Parameter(
                name="model",
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
                type="str",
                default_value=MODEL_REPO_IDS[0],
                tooltip="SeedVR2 model to use. ByteDance-Seed/SeedVR2-3B is faster; ByteDance-Seed/SeedVR2-7B produces higher quality results. Use the Model Manager to download SeedVR2 models before running.",
                traits={Options(choices=MODEL_REPO_IDS)},
            )
        )
        self.add_parameter(
            ParameterButton(
                name="model_manager",
                label="Open Model Manager",
                icon="download",
                variant="secondary",
                full_width=True,
                href="#model-management",
                tooltip="Open Model Manager to download the selected SeedVR2 model",
                allowed_modes={ParameterMode.PROPERTY},
                hide=True,
            )
        )

        self.add_parameter(
            ParameterVideo(
                name="input_video",
                allowed_modes={ParameterMode.INPUT},
                tooltip="Input video to upscale/restore.",
            )
        )

        self.add_parameter(
            Parameter(
                name="resize_mode",
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
                type="str",
                default_value="scale",
                tooltip="How to specify the output size. Scale multiplies input dimensions; Dimensions sets exact pixels.",
                traits={Options(choices=["scale", "dimensions"])},
            )
        )
        self.add_parameter(
            Parameter(
                name="scale",
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
                type="str",
                default_value="2x",
                tooltip="Upscale multiplier applied to the input video dimensions.",
                traits={Options(choices=["1.5x", "2x", "3x", "4x"])},
            )
        )
        self.add_parameter(
            ParameterInt(
                name="output_width",
                tooltip="Target output width in pixels.",
                default_value=1280,
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
                hide=True,
            )
        )
        self.add_parameter(
            ParameterInt(
                name="output_height",
                tooltip="Target output height in pixels.",
                default_value=720,
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
                hide=True,
            )
        )

        self.add_parameter(
            Parameter(
                name="batch_size",
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
                type="int",
                default_value=13,
                tooltip=(
                    "Frames processed per diffusion step — must be 4n+1 (1, 5, 9, 13, ...). "
                    "Reduce if VRAM runs out; increase for better temporal consistency."
                ),
            )
        )

        self.add_parameter(
            ParameterInt(
                name="temporal_overlap",
                tooltip=(
                    "Frames of overlap between adjacent batches. "
                    "Overlapping frames are blended with a Hann (cosine) window to hide batch seams. "
                    "0 disables blending. Must be less than batch_size."
                ),
                default_value=2,
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
            )
        )

        # Seed parameters — added after other params to control display order
        self._seed_param.add_input_parameters()

        self.add_parameter(
            ParameterVideo(
                name="output_video",
                allowed_modes={ParameterMode.OUTPUT},
                tooltip="Upscaled/restored video at the target resolution.",
            )
        )

        self._output_file = ProjectFileParameter(
            node=self,
            name="output_file",
            default_filename="seedvr2_video.mp4",
        )
        self._output_file.add_parameter()

        self._refresh_model_dropdown()

        # Status parameters MUST be last
        self._create_status_parameters()

    def after_value_set(self, parameter: Parameter, value: Any) -> None:
        super().after_value_set(parameter, value)
        self._seed_param.after_value_set(parameter, value)
        if parameter.name == "resize_mode":
            self._update_resize_mode_visibility()

    def after_incoming_connection(
        self,
        source_node: Any,
        source_parameter: Parameter,
        target_parameter: Parameter,
    ) -> None:
        if target_parameter.name == "input_video":
            value = source_node.get_parameter_value(source_parameter.name)
            logger.info("input_video connected: type=%s", type(value).__name__)
            if value is not None:
                self._update_params_from_video(value)
        super().after_incoming_connection(source_node, source_parameter, target_parameter)

    def _update_params_from_video(self, video_artifact: Any) -> None:
        if not isinstance(video_artifact, VideoUrlArtifact):
            logger.warning(
                "input_video: expected VideoUrlArtifact, got %s — skipping auto-detect", type(video_artifact).__name__
            )
            return
        try:
            fps, frame_count = _probe_video(str(File(video_artifact.value).resolve()))
            logger.info("Video probe: %.2f fps, %d frames", fps, frame_count)
            if frame_count > 0:
                self.set_parameter_value("batch_size", ideal_batch_size(frame_count))
            if fps <= 0:
                logger.warning("Could not determine fps from video probe")
        except Exception:
            logger.exception("Failed to read video metadata for fps/batch_size detection")

    def _get_seedvr_root(self) -> Path:
        assert __file__ is not None
        return Path(__file__).parent / "seedvr"

    def _update_resize_mode_visibility(self) -> None:
        mode = self.parameter_values.get("resize_mode") or "scale"
        if mode == "scale":
            self.show_parameter_by_name("scale")
            self.hide_parameter_by_name("output_width")
            self.hide_parameter_by_name("output_height")
        else:
            self.hide_parameter_by_name("scale")
            self.show_parameter_by_name("output_width")
            self.show_parameter_by_name("output_height")

    def _is_model_downloaded(self, repo_id: str) -> bool:
        try:
            from pathlib import Path as _Path  # noqa: PLC0415

            from huggingface_hub.constants import HF_HUB_CACHE  # noqa: PLC0415

            snapshots = _Path(HF_HUB_CACHE) / ("models--" + repo_id.replace("/", "--")) / "snapshots"
            return snapshots.exists() and any(snapshots.iterdir())
        except Exception:
            return False

    def _refresh_model_dropdown(self) -> None:
        data = []
        for repo_id in MODEL_REPO_IDS:
            if self._is_model_downloaded(repo_id):
                data.append({"name": repo_id, "icon": "check-circle", "subtitle": "Downloaded"})
            else:
                data.append({"name": repo_id, "icon": "download", "subtitle": "Not downloaded"})
        param = self.get_parameter_by_name("model")
        if param is not None:
            param.update_ui_options({"data": data, "dropdown_row_icons": True, "dropdown_row_subtitles": True})

    def validate_before_node_run(self) -> list[Exception] | None:
        errors: list[Exception] = []
        if self.parameter_values.get("input_video") is None:
            errors.append(ValueError("input_video is required"))
        model_repo_id = self.parameter_values.get("model") or MODEL_REPO_IDS[0]
        if model_repo_id in _MODEL_CONFIG:
            _, ckpt_file = _MODEL_CONFIG[model_repo_id]
            dit_ckpt = self._get_seedvr_root() / "ckpts" / ckpt_file
            if not dit_ckpt.exists():
                errors.append(
                    RuntimeError(
                        f"Model checkpoint not found for '{model_repo_id}'. "
                        "Download it via the Model Manager before running this node."
                    )
                )
        return errors if errors else None

    def process(self) -> AsyncResult[None]:
        self._clear_execution_status()
        try:
            yield lambda: self._do_inference()
            self._set_status_results(was_successful=True, result_details="SUCCESS: Video upscaled successfully")
        except Exception as e:
            logger.exception("SeedVR2 inference failed")
            self._set_status_results(
                was_successful=False,
                result_details=f"FAILURE: {type(e).__name__}: {e}",
            )
            self._handle_failure_exception(e)

    def _do_inference(self) -> None:  # noqa: PLR0912, PLR0915
        model_repo_id: str = self.parameter_values.get("model") or MODEL_REPO_IDS[0]
        logger.info("Starting inference with model=%s", model_repo_id)
        self._seed_param.preprocess()
        seed = self._seed_param.get_seed()

        resize_mode = self.parameter_values.get("resize_mode") or "scale"
        _output_height_fixed: int = self.parameter_values.get("output_height") or 720
        _output_width_fixed: int = self.parameter_values.get("output_width") or 1280
        _scale_str: str = self.parameter_values.get("scale") or "2x"
        batch_n = snap_to_4n1(self.parameter_values.get("batch_size") or 1)
        overlap_param = int(self.parameter_values.get("temporal_overlap") or 2)

        video_artifact = self.parameter_values.get("input_video")
        if not isinstance(video_artifact, VideoUrlArtifact):
            raise ValueError("input_video is required")

        seedvr_root = self._get_seedvr_root()
        ckpts_dir = seedvr_root / "ckpts"
        config_dir, ckpt_file = _MODEL_CONFIG[model_repo_id]
        config_path = seedvr_root / config_dir / "main.yaml"
        dit_ckpt = ckpts_dir / ckpt_file

        if not dit_ckpt.exists():
            raise RuntimeError(
                f"Model checkpoint not found for '{model_repo_id}'.\n"
                "Please download the model via the Model Manager before running this node."
            )

        original_cwd = os.getcwd()
        try:
            # REQUIRED: SeedVR uses os.getcwd()-relative paths for configs and checkpoints.
            os.chdir(str(seedvr_root))

            if str(seedvr_root) not in sys.path:
                sys.path.insert(0, str(seedvr_root))

            # Inject a flash_attn stub before any SeedVR model code is imported.
            # flash_attn has no Windows wheels so it may not be installed; the stub
            # implements flash_attn_varlen_func via PyTorch SDPA as a fallback.
            if "flash_attn" not in sys.modules:
                try:
                    import flash_attn  # noqa: F401
                except ImportError:
                    import types

                    import torch.nn.functional as F

                    def _flash_attn_varlen_func_sdpa(
                        q: torch.Tensor,
                        k: torch.Tensor,
                        v: torch.Tensor,
                        cu_seqlens_q: torch.Tensor,
                        cu_seqlens_k: torch.Tensor,
                        max_seqlen_q: int,
                        max_seqlen_k: int,
                        dropout_p: float = 0.0,
                        softmax_scale: float | None = None,
                        causal: bool = False,
                        **kwargs: object,
                    ) -> torch.Tensor:
                        if softmax_scale is None:
                            softmax_scale = q.shape[-1] ** -0.5
                        batch_size = len(cu_seqlens_q) - 1
                        outputs = []
                        for i in range(batch_size):
                            qs = int(cu_seqlens_q[i].item())
                            qe = int(cu_seqlens_q[i + 1].item())
                            ks = int(cu_seqlens_k[i].item())
                            ke = int(cu_seqlens_k[i + 1].item())
                            # (seqlen, nheads, dim) → (1, nheads, seqlen, dim)
                            qi = q[qs:qe].transpose(0, 1).unsqueeze(0)
                            ki = k[ks:ke].transpose(0, 1).unsqueeze(0)
                            vi = v[ks:ke].transpose(0, 1).unsqueeze(0)
                            out = F.scaled_dot_product_attention(qi, ki, vi, scale=softmax_scale, is_causal=causal)
                            # (1, nheads, seqlen, dim) → (seqlen, nheads, dim)
                            outputs.append(out.squeeze(0).transpose(0, 1))
                        return torch.cat(outputs, dim=0)

                    _stub = types.ModuleType("flash_attn")
                    _stub.flash_attn_varlen_func = _flash_attn_varlen_func_sdpa  # type: ignore[attr-defined]
                    sys.modules["flash_attn"] = _stub
                    logger.warning("flash_attn not installed — using PyTorch SDPA fallback")

            # Inject an apex stub before any SeedVR model code is imported.
            # apex has no Windows or general-PyPI wheels; the pre-built wheels from
            # ByteDance are Linux-only. The stub provides FusedLayerNorm (→ nn.LayerNorm)
            # and FusedRMSNorm (→ pure-PyTorch RMSNorm) so normalization.py loads cleanly.
            if "apex" not in sys.modules:
                try:
                    import apex  # noqa: F401
                except ImportError:
                    import types as _types

                    import torch.nn as nn

                    class _FusedLayerNorm(nn.LayerNorm):
                        def __init__(
                            self,
                            normalized_shape: int | list[int],
                            elementwise_affine: bool = True,
                            eps: float = 1e-5,
                            **kwargs: object,
                        ) -> None:
                            super().__init__(
                                normalized_shape,
                                eps=eps,
                                elementwise_affine=elementwise_affine,
                            )

                    class _FusedRMSNorm(nn.Module):
                        def __init__(
                            self,
                            normalized_shape: int | list[int],
                            elementwise_affine: bool = True,
                            eps: float = 1e-6,
                            **kwargs: object,
                        ) -> None:
                            super().__init__()
                            self.normalized_shape = normalized_shape
                            self.eps = eps
                            self.elementwise_affine = elementwise_affine
                            if elementwise_affine:
                                self.weight = nn.Parameter(torch.ones(normalized_shape))

                        def forward(self, x: torch.Tensor) -> torch.Tensor:
                            norm = x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)
                            if self.elementwise_affine:
                                norm = norm * self.weight
                            return norm

                    _apex_stub = _types.ModuleType("apex")
                    _apex_norm_stub = _types.ModuleType("apex.normalization")
                    _apex_norm_stub.FusedLayerNorm = _FusedLayerNorm  # type: ignore[attr-defined]
                    _apex_norm_stub.FusedRMSNorm = _FusedRMSNorm  # type: ignore[attr-defined]
                    _apex_stub.normalization = _apex_norm_stub  # type: ignore[attr-defined]
                    sys.modules["apex"] = _apex_stub
                    sys.modules["apex.normalization"] = _apex_norm_stub
                    logger.warning("apex not installed — using pure-PyTorch LayerNorm/RMSNorm fallback")

            # diffusers.models.lora conditionally imports CLIPTextModel from transformers.
            # transformers is on disk but its utils/ subpackage is missing on Windows
            # (260-char path limit), so `import transformers` fails with
            # "No module named 'transformers.utils'".
            # SeedVR uses none of the LoRA/CLIP features, so we disable the gate before
            # the DiT model module is dynamically loaded via importlib.import_module.
            try:
                import diffusers.utils.import_utils as _diu  # noqa: PLC0415

                if getattr(_diu, "_transformers_available", False):
                    _diu._transformers_available = False  # type: ignore[attr-defined]
                    logger.warning(
                        "diffusers: transformers package found but utils/ is missing "
                        "(Windows path limit). Disabled transformers gate to prevent "
                        "import error — SeedVR does not use CLIP/LoRA features."
                    )
            except Exception:
                pass

            # torch.distributed requires these env vars even for single-GPU inference
            os.environ.setdefault("MASTER_ADDR", "127.0.0.1")
            os.environ.setdefault("MASTER_PORT", "29500")
            os.environ.setdefault("RANK", "0")
            os.environ.setdefault("LOCAL_RANK", "0")
            os.environ.setdefault("WORLD_SIZE", "1")

            import torch.distributed as dist

            if not dist.is_initialized():
                # init_torch() hardcodes backend="nccl" which is Linux-only.
                # Use gloo on Windows (available on all platforms) and nccl elsewhere.
                torch.backends.cuda.matmul.allow_tf32 = True
                torch.backends.cudnn.allow_tf32 = True
                torch.backends.cudnn.benchmark = False
                torch.cuda.set_device(0)
                backend = "nccl" if sys.platform != "win32" else "gloo"
                dist.init_process_group(
                    backend=backend,
                    rank=0,
                    world_size=1,
                    timeout=datetime.timedelta(seconds=3600),
                )

            # Load or retrieve cached runner (avoids reloading weights on every execution)
            if model_repo_id not in SeedVR2VideoUpscale._RUNNER_CACHE:
                from common.config import load_config
                from omegaconf import OmegaConf
                from projects.video_diffusion_sr.infer import VideoDiffusionInfer

                config = load_config(str(config_path))
                runner = VideoDiffusionInfer(config)
                OmegaConf.set_readonly(runner.config, False)
                runner.configure_dit_model(device="cuda", checkpoint=str(dit_ckpt))
                runner.configure_vae_model()
                if hasattr(runner.vae, "set_memory_limit"):
                    runner.vae.set_memory_limit(**runner.config.vae.memory_limit)
                SeedVR2VideoUpscale._RUNNER_CACHE[model_repo_id] = runner

            runner = SeedVR2VideoUpscale._RUNNER_CACHE[model_repo_id]

            # SeedVR2 one-step configuration
            runner.config.diffusion.cfg.scale = 1.0
            runner.config.diffusion.cfg.rescale = 0.0
            runner.config.diffusion.timesteps.sampling.steps = 1
            runner.configure_diffusion()

            import numpy as np

            video_path = str(File(video_artifact.value).resolve())
            frames, raw_fps = _decode_video(video_path)
            if not frames:
                raise ValueError(
                    "Input video has 0 readable frames — the file may be corrupt "
                    f"or in an unsupported format: {video_path}"
                )

            total_frames = len(frames)
            input_fps = float(raw_fps if raw_fps > 0 else 24.0)

            # Compute output dimensions from first frame shape
            h0, w0 = frames[0].shape[0], frames[0].shape[1]
            if resize_mode == "scale":
                scale_factor = float(_scale_str.rstrip("x"))
                output_height = int(h0 * scale_factor)
                output_width = int(w0 * scale_factor)
            else:
                output_height = _output_height_fixed
                output_width = _output_width_fixed

            logger.info(
                "Input: %d frames at %.2f fps → output %dx%d", total_frames, input_fps, output_width, output_height
            )

            from common.distributed import get_device
            from common.distributed.ops import sync_data
            from common.seed import set_seed
            from data.image.transforms.divisible_crop import DivisibleCrop
            from data.image.transforms.na_resize import NaResize
            from data.video.transforms.rearrange import Rearrange
            from torchvision.transforms import Compose, Lambda, Normalize

            device = get_device()

            video_transform = Compose(
                [
                    NaResize(
                        resolution=(output_height * output_width) ** 0.5,
                        mode="area",
                        downsample_only=False,
                    ),
                    Lambda(lambda x: torch.clamp(x, 0.0, 1.0)),
                    DivisibleCrop((16, 16)),
                    Normalize(0.5, 0.5),
                    Rearrange("t c h w -> c t h w"),
                ]
            )

            # Pre-computed text embeddings are shared across all batches
            text_pos = torch.load(str(seedvr_root / "pos_emb.pt"), map_location=device)
            text_neg = torch.load(str(seedvr_root / "neg_emb.pt"), map_location=device)
            text_embeds: dict[str, list[torch.Tensor]] = {
                "texts_pos": [text_pos],
                "texts_neg": [text_neg],
            }

            # Build overlapping windows over the full frame list
            overlap = max(0, min(overlap_param, batch_n - 1))
            step = max(1, batch_n - overlap)
            windows = _make_windows(total_frames, batch_n, step)
            logger.info(
                "Processing %d windows (batch=%d, overlap=%d, step=%d)",
                len(windows),
                batch_n,
                overlap,
                step,
            )
            n_windows = len(windows)

            # Output accumulators on CPU — avoids holding VRAM during accumulation
            output_acc: torch.Tensor | None = None
            weight_acc: torch.Tensor | None = None

            sp_size = 1
            cond_noise_scale = 0.0

            for win_idx, (win_start, win_end) in enumerate(windows):
                n_win = win_end - win_start
                batch_np = np.stack(frames[win_start:win_end], axis=0)  # (T, H, W, C) uint8
                batch_tensor = torch.from_numpy(batch_np).permute(0, 3, 1, 2).float() / 255.0

                cond_tensor = video_transform(batch_tensor.to(device))  # (C, T, H, W)

                # Pad temporal dim to nearest 4n+1 required by the VAE
                t = cond_tensor.shape[1]
                if t > 1:
                    if t <= 4 * sp_size:
                        pad_count = 4 * sp_size - t + 1
                        cond_tensor = torch.cat([cond_tensor] + [cond_tensor[:, -1:]] * pad_count, dim=1)
                    elif (t - 1) % (4 * sp_size) != 0:
                        pad_count = 4 * sp_size - ((t - 1) % (4 * sp_size))
                        cond_tensor = torch.cat([cond_tensor] + [cond_tensor[:, -1:]] * pad_count, dim=1)

                # Phase 1: VAE encode — VAE on GPU, DiT on CPU
                runner.vae.to(device)
                runner.dit.to("cpu")
                cond_latents = runner.vae_encode([cond_tensor])
                runner.vae.to("cpu")
                _clear_vram()

                # Phase 2: DiT inference + VAE decode — DiT on GPU
                runner.dit.to(device)
                set_seed(seed + win_idx, same_across_ranks=True)

                noises = [torch.randn_like(latent) for latent in cond_latents]
                aug_noises = [torch.randn_like(latent) for latent in cond_latents]
                noises, aug_noises, cond_latents = sync_data((noises, aug_noises, cond_latents), 0)
                noises = [n.to(device) for n in noises]
                aug_noises = [n.to(device) for n in aug_noises]
                cond_latents = [n.to(device) for n in cond_latents]

                def _add_noise(x: torch.Tensor, aug_noise: torch.Tensor) -> torch.Tensor:
                    t_val = torch.tensor([1000.0], device=device) * cond_noise_scale
                    shape = torch.tensor(x.shape[1:], device=device)[None]
                    t_shifted = runner.timestep_transform(t_val, shape)
                    return runner.schedule.forward(x, aug_noise, t_shifted)  # type: ignore[union-attr]

                conditions = [
                    runner.get_condition(noise, task="sr", latent_blur=_add_noise(latent_blur, aug_noise))
                    for noise, aug_noise, latent_blur in zip(noises, aug_noises, cond_latents, strict=False)
                ]

                with torch.no_grad(), torch.autocast("cuda", torch.bfloat16, enabled=True):
                    video_tensors = runner.inference(
                        noises=noises,
                        conditions=conditions,
                        dit_offload=True,
                        **text_embeds,
                    )

                samples = [
                    rearrange(v[:, None], "c t h w -> t c h w") if v.ndim == 3 else rearrange(v, "c t h w -> t c h w")
                    for v in video_tensors
                ]
                del video_tensors, conditions, noises, aug_noises, cond_latents, cond_tensor, batch_tensor

                runner.dit.to("cpu")
                _clear_vram()

                sample = samples[0].cpu()  # (T, C, H, W) float in [-1, 1]
                sample = sample[:n_win]  # trim temporal padding

                # Initialize accumulators once we know actual output H/W
                if output_acc is None:
                    out_c, out_h, out_w = sample.shape[1], sample.shape[2], sample.shape[3]
                    # float16 halves RAM vs float32; blending precision is sufficient
                    output_acc = torch.zeros(total_frames, out_c, out_h, out_w, dtype=torch.float16)
                    weight_acc = torch.zeros(total_frames, 1, 1, 1, dtype=torch.float16)

                assert output_acc is not None
                assert weight_acc is not None

                is_first = win_idx == 0
                is_last = win_idx == len(windows) - 1
                weights = _compute_hann_weights(n_win, overlap, is_first, is_last).view(-1, 1, 1, 1)

                output_acc[win_start : win_start + n_win] += sample * weights
                weight_acc[win_start : win_start + n_win] += weights

                del sample, samples
                logger.info("Window %d/%d complete", win_idx + 1, n_windows)

            assert output_acc is not None and weight_acc is not None

            # Normalize in-place — avoids a second full-size tensor copy at large scales
            assert output_acc is not None and weight_acc is not None
            output_acc /= weight_acc.clamp(min=1e-4)
            del weight_acc
            sample_hwc = rearrange(output_acc, "t c h w -> t h w c")
            sample_np = sample_hwc.clip(-1, 1).mul_(0.5).add_(0.5).mul_(255).round_().to(torch.uint8).numpy()
            del sample_hwc, output_acc

            out_fps = input_fps

            import mediapy

            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as out_tmp:
                out_path = out_tmp.name
            try:
                mediapy.write_video(out_path, sample_np, fps=out_fps)
                with open(out_path, "rb") as f:
                    video_bytes = f.read()
            finally:
                os.unlink(out_path)

            file_dest = self._output_file.build_file()
            saved = file_dest.write_bytes(video_bytes)
            self.parameter_output_values["output_video"] = VideoUrlArtifact(saved.location)

            _clear_vram()

        finally:
            os.chdir(original_cwd)
