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
from griptape.artifacts import ImageArtifact, ImageUrlArtifact
from griptape.artifacts.video_url_artifact import VideoUrlArtifact
from griptape_nodes.exe_types.core_types import Parameter, ParameterMode
from griptape_nodes.exe_types.node_types import AsyncResult, SuccessFailureNode
from griptape_nodes.exe_types.param_components.huggingface.huggingface_repo_parameter import HuggingFaceRepoParameter
from griptape_nodes.exe_types.param_components.project_file_parameter import ProjectFileParameter
from griptape_nodes.exe_types.param_components.seed_parameter import SeedParameter
from griptape_nodes.exe_types.param_types.parameter_video import ParameterVideo
from griptape_nodes.files.file import File
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


class SeedVR2VideoUpscale(SuccessFailureNode):
    """Upscale and restore video using SeedVR2 diffusion transformer from ByteDance."""

    _RUNNER_CACHE: dict[str, Any] = {}

    def __init__(self, name: str, metadata: dict[Any, Any] | None = None) -> None:
        super().__init__(name, metadata)

        # SeedParameter FIRST — must exist before any add_parameter calls because
        # after_value_set can fire during parameter initialization.
        self._seed_param = SeedParameter(self)

        # HuggingFace model selection — reads locally-cached HF repos
        self._model_param = HuggingFaceRepoParameter(
            self,
            repo_ids=MODEL_REPO_IDS,
            parameter_name="model",
        )
        self._model_param.add_input_parameters()

        self.add_parameter(
            ParameterVideo(
                name="input_video",
                allowed_modes={ParameterMode.INPUT},
                tooltip="Input video to upscale/restore.",
            )
        )

        self.add_parameter(
            Parameter(
                name="output_height",
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
                type="int",
                default_value=720,
                tooltip="Target output height in pixels.",
            )
        )
        self.add_parameter(
            Parameter(
                name="output_width",
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
                type="int",
                default_value=1280,
                tooltip="Target output width in pixels.",
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

        # Status parameters MUST be last
        self._create_status_parameters()

    def after_value_set(self, parameter: Parameter, value: Any) -> None:
        super().after_value_set(parameter, value)
        self._seed_param.after_value_set(parameter, value)
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
            import cv2

            path = File(video_artifact.value).resolve()
            cap = cv2.VideoCapture(path)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            cap.release()
            if frame_count > 0:
                self.set_parameter_value("batch_size", ideal_batch_size(frame_count))
            if fps > 0:
                self.set_parameter_value("output_fps", float(fps))
        except Exception:
            pass

    def _get_seedvr_root(self) -> Path:
        assert __file__ is not None
        return Path(__file__).parent / "seedvr"

    def validate_before_node_run(self) -> list[Exception] | None:
        errors: list[Exception] = []
        hf_errors = self._model_param.validate_before_node_run()
        if hf_errors:
            errors.extend(hf_errors)
        if self.parameter_values.get("input_video") is None:
            errors.append(ValueError("input_video is required"))
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
        model_repo_id, _ = self._model_param.get_repo_revision()
        self._seed_param.preprocess()
        seed = self._seed_param.get_seed()

        output_height: int = self.parameter_values.get("output_height") or 720
        output_width: int = self.parameter_values.get("output_width") or 1280
        snap_to_4n1(self.parameter_values.get("batch_size") or 1)
        output_fps_param: float | None = self.parameter_values.get("output_fps")

        video_artifact = self.parameter_values.get("input_video")
        if not isinstance(video_artifact, (VideoUrlArtifact, ImageUrlArtifact, ImageArtifact)):
            raise ValueError("input_video is required")

        seedvr_root = self._get_seedvr_root()
        ckpts_dir = seedvr_root / "ckpts"
        config_dir, ckpt_file = _MODEL_CONFIG[model_repo_id]
        config_path = seedvr_root / config_dir / "main.yaml"
        dit_ckpt = ckpts_dir / ckpt_file

        if not dit_ckpt.exists():
            from huggingface_hub import snapshot_download

            logger.info("Downloading %s to %s ...", model_repo_id, ckpts_dir)
            snapshot_download(  # type: ignore[call-overload]
                repo_id=model_repo_id,
                local_dir=str(ckpts_dir),
                allow_patterns=["*.pth", "*.safetensors", "*.json", "*.txt"],
                local_dir_use_symlinks=False,
                resume_download=True,
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

            # Decode input to bytes
            is_image = isinstance(video_artifact, (ImageUrlArtifact, ImageArtifact))
            suffix = ".png" if is_image else ".mp4"
            if isinstance(video_artifact, ImageArtifact):
                input_bytes = video_artifact.value
            else:
                input_bytes = File(video_artifact.value).read_bytes()

            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(input_bytes)
                tmp_path = tmp.name

            try:
                from torchvision.io import read_image
                from torchvision.io.video import read_video

                if is_image:
                    video_tensor = read_image(tmp_path).unsqueeze(0) / 255.0
                    input_fps = float(output_fps_param or 24.0)
                else:
                    video_tensor, _, info = read_video(tmp_path, output_format="TCHW")
                    video_tensor = video_tensor / 255.0
                    input_fps = float(info.get("video_fps", 24.0))
            finally:
                os.unlink(tmp_path)

            original_frame_count = video_tensor.shape[0]
            logger.info("Input: %d frames, fps=%.2f", original_frame_count, input_fps)

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
