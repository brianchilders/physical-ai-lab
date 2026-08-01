# Storage Plan

This lab uses `/mnt/nvme/isaac` as the canonical storage root for large, local, reproducible Isaac Sim work.

## Target Layout

```text
/mnt/nvme/isaac/
├── cache/
│   ├── isaac-sim/
│   │   ├── computecache/
│   │   └── main/
│   └── ov/
│       └── hub/
├── assets/
├── datasets/
├── logs/
│   └── isaac-sim/
└── projects/
    └── isaac-sim/
        ├── config/
        ├── data/
        └── pkg/
```

## Directory Purpose

- `/mnt/nvme/isaac/cache/`: package caches, Docker-adjacent caches, downloaded models, and temporary build artifacts.
- `/mnt/nvme/isaac/assets/`: reusable assets such as meshes, textures, calibrated sensor files, and USD resources.
- `/mnt/nvme/isaac/datasets/`: raw and processed datasets from experiments and sensors.
- `/mnt/nvme/isaac/logs/`: run output, telemetry, debugging traces, and experiment logs.
- `/mnt/nvme/isaac/projects/`: active project checkouts, sandboxes, and experimental worktrees.

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
- experiment runtime trees may live under `/mnt/nvme/isaac/experiments/<phase>/` with separate `output/`, `results/`, cache, config, data, and log subdirectories
- Phase 6 uses `/mnt/nvme/isaac/experiments/004-physics-foundations/` as the canonical runtime tree, while the only tracked runtime-adjacent result artifact is the sanitized `results/summary.md`
