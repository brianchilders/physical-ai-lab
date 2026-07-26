# Storage Plan

This lab uses `/mnt/nvme` as the canonical storage root for large, local, reproducible work.

## Target Layout

```text
/mnt/nvme/
├── isaac/
├── cache/
├── assets/
├── datasets/
├── logs/
└── projects/
```

## Directory Purpose

- `/mnt/nvme/isaac/`: Isaac Sim installation payloads, runtime state, and simulator-specific files.
- `/mnt/nvme/cache/`: package caches, Docker caches, downloaded models, and temporary build artifacts.
- `/mnt/nvme/assets/`: reusable assets such as meshes, textures, calibrated sensor files, and USD resources.
- `/mnt/nvme/datasets/`: raw and processed datasets from experiments and sensors.
- `/mnt/nvme/logs/`: run output, telemetry, debugging traces, and experiment logs.
- `/mnt/nvme/projects/`: active project checkouts, sandboxes, and experimental worktrees.

## Repository vs NVMe

Tracked repository directories are not the canonical location for large data.

Use the repository for:

- manifests
- metadata
- configuration
- documentation
- small illustrative examples

Use NVMe for:

- large binaries
- simulator installs
- datasets
- logs
- caches

## Practical Notes

- keep data paths explicit in docs and config
- never assume a hidden default location for simulator state
- document the mount points before adding automation that depends on them
