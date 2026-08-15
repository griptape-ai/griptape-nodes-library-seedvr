# SeedVR2 Upscale

A [Griptape Nodes](https://www.griptapenodes.com/) library for video and image super-resolution using [SeedVR2](https://github.com/ByteDance-Seed/SeedVR) from ByteDance.

SeedVR2 (ICLR 2026) upscales footage in a single diffusion step via adversarial post-training — dramatically faster than multi-step predecessors while preserving fine detail, texture, and motion.

---

## Why SeedVR2?

Most upscalers either smear detail (interpolation) or require dozens of denoising steps (standard diffusion). SeedVR2 does neither. It combines the quality of a diffusion model with the speed of a single-step inference, which means you can upscale a short clip in seconds and a full scene in minutes rather than hours.

Use it to:

- **Restore degraded footage** — sharpen and denoise video or stills before passing them downstream
- **Scale up AI-generated video** — generate at lower resolution for speed, then upscale for final output
- **Prepare frames for editing** — bring archival or low-resolution media up to modern standards
- **Build upscale pipelines** — wire the output directly into grading, compositing, or export nodes

---

## Nodes

### SeedVR2 Video Upscale

Upscales a video clip using a SeedVR2 diffusion transformer. Processes frames in overlapping batches for temporal consistency.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| model | Dropdown | `SeedVR2-3B` | Model variant. 3B fits on a 24 GB GPU; 7B needs 40–80 GB VRAM. |
| input_video | VideoUrlArtifact | — | Source video to upscale. |
| resize_mode | Dropdown | `scale` | **Scale**: multiply input dimensions by a factor. **Dimensions**: set exact output pixels. |
| scale | Dropdown | `2x` | Multiplier applied to the input resolution (1.5×, 2×, 3×, 4×). Visible in Scale mode. |
| output_width / output_height | int | 1280 / 720 | Exact output size. Visible in Dimensions mode. |
| batch_size | int | 1 | Frames per diffusion step. Values follow the 4n+1 pattern (1, 5, 9, 13 …). |
| output_fps | float | — | Output frame rate. Preserves source FPS when left blank. |
| seed / randomize_seed | int / bool | 666 / false | Reproducibility controls. |

**Output**: `output_video` — upscaled video saved to the project file directory.

---

### SeedVR2 Image Upscale

Upscales a single image using the same SeedVR2 diffusion backbone as the video node.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| model | Dropdown | `SeedVR2-3B` | Model variant. |
| input_image | ImageUrlArtifact | — | Source image to upscale. |
| resize_mode | Dropdown | `scale` | **Scale** or **Dimensions** — same behaviour as the video node. |
| scale | Dropdown | `2x` | Multiplier (1.5×, 2×, 3×, 4×). Visible in Scale mode. |
| output_width / output_height | int | 1280 / 720 | Exact output size. Visible in Dimensions mode. |
| seed / randomize_seed | int / bool | 666 / false | Reproducibility controls. |

**Output**: `output_image` — upscaled image saved to the project file directory.

---

## Models

| Repo ID | VRAM | Notes |
|---------|------|-------|
| `ByteDance-Seed/SeedVR2-3B` | ~24 GB | Single RTX 4090; recommended starting point |
| `ByteDance-Seed/SeedVR2-7B` | ~40–80 GB | Higher quality; requires A100 / H100 class GPU |

Models are downloaded from HuggingFace through the **Model Manager** inside Griptape Nodes. Both nodes show a **Download in Model Manager** button when the selected model is not yet cached locally — click it to open the Model Manager directly. Once downloaded, the button disappears and the model name gains a checkmark in the dropdown.

> **Storage**: HuggingFace caches models at `~/.cache/huggingface/hub` (Linux/macOS) or `%USERPROFILE%\.cache\huggingface\hub` (Windows). Set the `HF_HOME` environment variable before launching the engine to store them elsewhere.

---

## Requirements

- **GPU**: NVIDIA CUDA GPU required.
  - 3B model: minimum RTX 4090 (24 GB VRAM) for short clips up to 720p
  - 7B model: A100 40 GB or H100 80 GB for longer or higher-resolution clips
- **OS**: Linux (CUDA). Windows support is limited by the upstream SeedVR repo.
- **Python**: 3.10 recommended (pre-built NVIDIA apex wheels are available for 3.9 and 3.10).

---

## Installation

1. In Griptape Nodes, open **Manage → Library Management**
2. Paste in the repository URL:
   ```
   https://github.com/griptape-ai/griptape-nodes-library-seedvr.git
   ```
3. Click **Download**

On first use, the library automatically:

1. Initializes the SeedVR git submodule
2. Installs SeedVR's `requirements.txt` dependencies into the library venv
3. Installs `flash_attn` and the NVIDIA apex wheel (requires torch; uses `--no-build-isolation`)

After installation, look for **SeedVR2 Video Upscale** in the `video` category and **SeedVR2 Image Upscale** in the `image` category in the node picker.

---

## Development

```bash
# Install dev dependencies
make install

# Auto-fix formatting and lint issues
make fix

# Full check (format, lint, types, JSON)
make check
```

---

## License

This library wrapper is Apache 2.0 licensed. The SeedVR model code and weights are also licensed under [Apache 2.0](https://github.com/ByteDance-Seed/SeedVR/blob/main/LICENSE).