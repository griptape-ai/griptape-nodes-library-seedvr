# Griptape Nodes SeedVR Library

Video and image super-resolution using [SeedVR2](https://github.com/ByteDance-Seed/SeedVR) diffusion transformers from ByteDance.

SeedVR2 (ICLR 2026) achieves high-fidelity upscaling in a single diffusion step via adversarial post-training, making it dramatically faster than multi-step predecessors while retaining comparable quality.

## Requirements

- **GPU**: NVIDIA CUDA GPU required. Recommended minimum: RTX 4090 (24 GB) for short clips at 720p. H100 80 GB for 100-frame 720p or longer.
- **OS**: Linux (CUDA). Windows is not supported by the upstream SeedVR repo.
- **Python**: 3.10 or 3.9 (pre-built NVIDIA apex wheels are available for these versions only).

## Nodes

### SeedVR2 Video Upscale

Upscales and restores a video (or single image) using SeedVR2.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| model | HuggingFace repo | `SeedVR2-3B` | Model variant. 3B fits on a 24 GB GPU; 7B needs 40–80 GB VRAM. |
| input_video | VideoUrlArtifact | — | Input video. Connect an image for single-frame upscaling. |
| output_height | int | 720 | Target output height in pixels. |
| output_width | int | 1280 | Target output width in pixels. |
| batch_size | int | auto | Frames per diffusion step (4n+1: 1, 5, 9, 13, …). Auto-set when input is connected. |
| color_correction | str | none | Color correction mode. Only `none` in v1 (see note below). |
| output_fps | float | — | Output FPS. Preserves source FPS if unset. |
| seed / randomize_seed | int / bool | 666 / false | Reproducibility control. |

**Output**: `output_video` — upscaled video saved to the project file location.

## Models

| Repo ID | Size | Notes |
|---------|------|-------|
| `ByteDance-Seed/SeedVR2-3B` | ~12–15 GB | Single 24 GB GPU; fast |
| `ByteDance-Seed/SeedVR2-7B` | ~28–30 GB | Higher quality; needs 40–80 GB VRAM |

Models are downloaded automatically from HuggingFace on first run and cached in `griptape_nodes_library_seedvr/seedvr/ckpts/`.

## Installation

This library is installed via the Griptape Nodes engine. The first run will:

1. Initialize the SeedVR git submodule.
2. Install SeedVR's `requirements.txt` dependencies into the library venv.
3. Install `flash_attn==2.5.9.post1` (requires torch to be pre-installed; uses `--no-build-isolation`).
4. Download and install a pre-built NVIDIA apex wheel from the SeedVR2 HuggingFace repo (Python 3.10 or 3.9 only).

## Color Correction Note

Wavelet and LAB color correction modes require `color_fix.py` from [pkuliyi2015/sd-webui-stablesr](https://github.com/pkuliyi2015/sd-webui-stablesr), which is GPL-licensed and cannot be bundled with this library. To enable it manually:

1. Download `color_fix.py` from that repo.
2. Place it at `griptape_nodes_library_seedvr/seedvr/projects/video_diffusion_sr/color_fix.py`.
3. A future library version will detect the file and expose wavelet/lab options automatically.

## Development

```bash
# Install dev dependencies
make install

# Lint and format
make fix

# Full check (format, lint, types, JSON)
make check
```

## License

This library wrapper is MIT licensed. The SeedVR model code and weights are licensed under [Apache 2.0](https://github.com/ByteDance-Seed/SeedVR/blob/main/LICENSE).
