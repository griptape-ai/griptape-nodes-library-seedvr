# Changelog

All notable changes to the Griptape Nodes SeedVR Library will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/2.0.0/), and each version is
the `library_version` in `griptape-nodes-library.json`.
**Breaking** marks a change that can stop a saved workflow from working without edits.

## [Unreleased]

<!-- Entries go in changelog.d/, one file each. See changelog.d/README.md. -->

## [0.3.0] - 2026-11-06

### Changed

- SeedVR2 Image Upscale and SeedVR2 Video Upscale report a missing input, a model that is not
  downloaded and a non-CUDA machine with plain messages that name the parameter and say what to do.
  A missing model links to the Model Manager. The status text no longer starts with the exception
  type for these errors. Requires engine 0.105.0 or later.
  [#9](https://github.com/griptape-ai/griptape-nodes-library-seedvr/issues/9)

[Unreleased]: https://github.com/griptape-ai/griptape-nodes-library-seedvr/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/griptape-ai/griptape-nodes-library-seedvr/compare/e910f540ebc848d7e0938f97b8720759c8ed8b48...v0.3.0
