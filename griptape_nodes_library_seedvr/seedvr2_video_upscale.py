import datetime
import gc
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

import torch
from einops import rearrange
from griptape.artifacts.video_url_artifact import VideoUrlArtifact
from griptape_nodes.exe_types.core_types import Parameter, ParameterMode
from griptape_nodes.exe_types.param_types.parameter_int import ParameterInt
from griptape_nodes.exe_types.node_types import AsyncResult, SuccessFailureNode
from griptape_nodes.exe_types.core_types import NodeMessageResult
from griptape_nodes.exe_types.param_components.project_file_parameter import ProjectFileParameter
from griptape_nodes.exe_types.param_components.seed_parameter import SeedParameter
from griptape_nodes.exe_types.param_types.parameter_button import ParameterButton
from griptape_nodes.exe_types.param_types.parameter_video import ParameterVideo
from griptape_nodes.files.file import File
from griptape_nodes.traits.button import Button, ButtonDetailsMessagePayload, OnClickMessageResultPayload
from griptape_nodes.traits.options import Options

logger = logging.getLogger("seedvr_library")

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
        container = av.open(buf)
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
                tooltip=(
                    "SeedVR2 model to use. Download models via the Model Manager before running. "
                    "3B is faster; 7B produces higher quality results."
                ),
                traits={Options(choices=MODEL_REPO_IDS)},
            )
        )

        self.add_parameter(
            ParameterButton(
                name="model_download",
                label="Open Model Manager to Download",
                icon="download",
                variant="secondary",
                full_width=True,
                on_click=self._on_model_manager_click,
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
            ParameterInt(
                name="output_width",
                tooltip="Target output width in pixels.",
                default_value=1280,
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
            )
        )
        self.add_parameter(
            ParameterInt(
                name="output_height",
                tooltip="Target output height in pixels.",
                default_value=720,
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
            )
        )

        self.add_parameter(
            Parameter(
                name="batch_size",
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
                type="int",
                default_value=1,
                tooltip=(
                    "Frames per diffusion step — must be 4n+1 (1, 5, 9, 13, ...). "
                    "Auto-set from video frame count when input is connected. "
                    "Reduce if VRAM runs out; increase for better temporal consistency."
                ),
            )
        )

        self.add_parameter(
            Parameter(
                name="color_correction",
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
                type="str",
                default_value="none",
                tooltip=(
                    "Post-processing color correction. "
                    "Only 'none' supported in v1 — wavelet/lab modes require "
                    "GPL-licensed color_fix.py which cannot be bundled."
                ),
                traits={Options(choices=["none"])},
            )
        )

        self.add_parameter(
            Parameter(
                name="output_fps",
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
                type="float",
                default_value=None,
                tooltip="Output video FPS. If unset, preserves the input video's original FPS.",
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
        if parameter.name == "model":
            self._update_download_button_visibility()
        if parameter.name == "input_video" and value is not None:
            self._update_params_from_video(value)

    def after_incoming_connection(
        self,
        source_node: Any,
        source_parameter: Parameter,
        target_parameter: Parameter,
    ) -> None:
        super().after_incoming_connection(source_node, source_parameter, target_parameter)
        if target_parameter.name == "input_video":
            value = self.parameter_values.get("input_video")
            if value is not None:
                self._update_params_from_video(value)

    def _update_params_from_video(self, video_artifact: Any) -> None:
        if not isinstance(video_artifact, VideoUrlArtifact):
            return
        try:
            fps, frame_count = _probe_video(str(File(video_artifact.value).resolve()))
            if frame_count > 0:
                self.set_parameter_value("batch_size", ideal_batch_size(frame_count))
            if fps > 0:
                self.set_parameter_value("output_fps", float(fps))
            else:
                logger.warning("Could not determine fps from video — output_fps not auto-set")
        except Exception:
            logger.exception("Failed to read video metadata for fps/batch_size detection")

    def _get_seedvr_root(self) -> Path:
        assert __file__ is not None
        return Path(__file__).parent / "seedvr"

    def _is_model_downloaded(self, repo_id: str) -> bool:
        try:
            from huggingface_hub.constants import HF_HUB_CACHE  # noqa: PLC0415
            from pathlib import Path as _Path  # noqa: PLC0415
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
        self._update_download_button_visibility()

    def _update_download_button_visibility(self) -> None:
        model_repo_id = self.parameter_values.get("model") or MODEL_REPO_IDS[0]
        if self._is_model_downloaded(model_repo_id):
            self.hide_parameter_by_name("model_download")
        else:
            self.show_parameter_by_name("model_download")

    def _on_model_manager_click(
        self, _button: Button, button_details: ButtonDetailsMessagePayload
    ) -> NodeMessageResult:
        model_repo_id = self.parameter_values.get("model") or MODEL_REPO_IDS[0]
        return NodeMessageResult(
            success=True,
            details="Opening Model Manager",
            response=OnClickMessageResultPayload(
                button_details=button_details,
                href=f"#model-management?search={model_repo_id}",
            ),
            altered_workflow_state=False,
        )

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
        yield lambda: self._run_inference()

    def _run_inference(self) -> None:
        try:
            self._do_inference()
        except Exception as e:
            logger.exception("SeedVR2 inference failed")
            self._set_status_results(
                was_successful=False,
                result_details=f"FAILURE: {type(e).__name__}: {e}",
            )
            self._handle_failure_exception(e)

    def _do_inference(self) -> None:
        model_repo_id: str = self.parameter_values.get("model") or MODEL_REPO_IDS[0]
        self._seed_param.preprocess()
        seed = self._seed_param.get_seed()

        output_height: int = self.parameter_values.get("output_height") or 720
        output_width: int = self.parameter_values.get("output_width") or 1280
        snap_to_4n1(self.parameter_values.get("batch_size") or 1)
        output_fps_param: float | None = self.parameter_values.get("output_fps")

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
            video_np = np.stack(frames, axis=0)  # (T, H, W, C) uint8
            video_tensor = torch.from_numpy(video_np).permute(0, 3, 1, 2).float() / 255.0
            input_fps = float(output_fps_param or (raw_fps if raw_fps > 0 else 24.0))

            original_frame_count = video_tensor.shape[0]
            logger.info("Input: %d frames, fps=%.2f", original_frame_count, input_fps)
            if original_frame_count == 0:
                raise ValueError("Input has 0 frames — cannot run inference on an empty video.")

            from common.distributed import get_device
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

            cond_tensor = video_transform(video_tensor.to(device))

            # Pad temporal dimension to 4*sp_size alignment (sp_size=1 for single GPU)
            sp_size = 1
            t = cond_tensor.shape[1]
            if t > 1:
                if t <= 4 * sp_size:
                    pad_count = 4 * sp_size - t + 1
                    cond_tensor = torch.cat([cond_tensor] + [cond_tensor[:, -1:]] * pad_count, dim=1)
                elif (t - 1) % (4 * sp_size) != 0:
                    pad_count = 4 * sp_size - ((t - 1) % (4 * sp_size))
                    cond_tensor = torch.cat([cond_tensor] + [cond_tensor[:, -1:]] * pad_count, dim=1)

            # Pre-computed text embeddings are shipped in the SeedVR repo root
            text_pos = torch.load(str(seedvr_root / "pos_emb.pt"), map_location=device)
            text_neg = torch.load(str(seedvr_root / "neg_emb.pt"), map_location=device)
            text_embeds: dict[str, list[torch.Tensor]] = {
                "texts_pos": [text_pos],
                "texts_neg": [text_neg],
            }

            # Offload DiT to CPU while VAE encodes to stay within VRAM budget
            runner.vae.to(device)
            runner.dit.to("cpu")
            cond_latents = runner.vae_encode([cond_tensor])
            runner.vae.to("cpu")
            runner.dit.to(device)

            from common.seed import set_seed

            set_seed(seed, same_across_ranks=True)

            from common.distributed.ops import sync_data

            noises = [torch.randn_like(latent) for latent in cond_latents]
            aug_noises = [torch.randn_like(latent) for latent in cond_latents]

            noises, aug_noises, cond_latents = sync_data((noises, aug_noises, cond_latents), 0)
            noises = [n.to(device) for n in noises]
            aug_noises = [n.to(device) for n in aug_noises]
            cond_latents = [n.to(device) for n in cond_latents]

            # cond_noise_scale=0.0 makes _add_noise an identity (no augmentation noise)
            cond_noise_scale = 0.0

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

            # Rearrange model output: (C, T, H, W) or (C, H, W) → (T, C, H, W)
            samples = [
                rearrange(v[:, None], "c t h w -> t c h w") if v.ndim == 3 else rearrange(v, "c t h w -> t c h w")
                for v in video_tensors
            ]
            del video_tensors
            runner.dit.to("cpu")

            sample = samples[0].to("cpu")
            if original_frame_count < sample.shape[0]:
                sample = sample[:original_frame_count]

            # (T, C, H, W) → (T, H, W, C) uint8 numpy for mediapy
            sample_hwc = rearrange(sample, "t c h w -> t h w c")
            sample_np = sample_hwc.clip(-1, 1).mul_(0.5).add_(0.5).mul_(255).round_().to(torch.uint8).numpy()

            out_fps = output_fps_param if output_fps_param is not None else input_fps

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
            self._set_status_results(was_successful=True, result_details="SUCCESS: Video upscaled successfully")

            gc.collect()
            torch.cuda.empty_cache()

        finally:
            os.chdir(original_cwd)
