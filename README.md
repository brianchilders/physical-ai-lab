# Physical AI Lab

This repository is the long-term home for robotics, simulation, perception, AI inference, and experimentation across the Physical AI lab.

Phase 1 establishes the engineering foundation only:

- repository structure
- documentation-first workflow
- storage conventions for `/mnt/nvme`
- future-ready Isaac Sim Docker layout
- notebook, experiment, asset, and dataset organization
- roadmap and milestone tracking

Isaac Sim is not being installed yet. ROS 2 is intentionally deferred.

## Current Hardware

- Development workstation: `blackmagic`
- OS: Ubuntu 24.04.4 LTS
- GPU: NVIDIA TITAN RTX, 24 GB VRAM
- Driver: NVIDIA 595.84
- CUDA runtime: 13.2
- CUDA toolkit: 12.0
- Docker with NVIDIA Container Toolkit
- Vulkan verified
- Docker GPU passthrough verified
- Memory: 125 GB RAM
- Local NVMe: 1.8 TB mounted at `/mnt/nvme`

Additional devices planned for integration:

- NVIDIA DGX Spark
- Intel RealSense D435
- Luxonis OAK-D Lite
- NVIDIA Jetson Orin Nano 8 GB
- Raspberry Pi edge systems

## Repository Intent

The repo is structured as an engineering notebook and reproducible lab, not just a codebase.

- Documentation comes before implementation.
- Large binaries and generated data live on NVMe, not in git.
- Docker is the preferred runtime boundary where practical.
- Each experiment should be reproducible from a documented configuration and a known storage location.

## Proposed Layout

```text
.
├── README.md
├── assets/
├── config/
├── datasets/
├── docker/
│   └── isaac/
├── docs/
├── experiments/
└── notebooks/
```

Supporting documentation:

- [Project Vision](docs/vision.md)
- [Architecture](docs/architecture.md)
- [Storage Plan](docs/storage.md)
- [Development Workflow](docs/workflow.md)
- [Roadmap](docs/roadmap.md)
- [Milestones](docs/milestones.md)

## Phase Plan

1. Phase 1: platform foundation, documentation, and repository organization.
2. Phase 2: Isaac Sim installation and validation in Docker.
3. Phase 3: controlled experiment harnesses, USD scene structure, and asset pipeline.
4. Phase 4: ROS 2 integration and sensor/device bring-up.
5. Phase 5: distributed inference and lab-scale automation, including DGX Spark integration.

## Storage Convention

The canonical storage root is `/mnt/nvme`.

- `/mnt/nvme/isaac/` for Isaac Sim installs, runtime payloads, and simulator-specific state.
- `/mnt/nvme/cache/` for Docker, package, model, and tool caches.
- `/mnt/nvme/assets/` for reusable meshes, textures, calibration artifacts, and USD resources.
- `/mnt/nvme/datasets/` for raw and processed experiment data.
- `/mnt/nvme/logs/` for run logs, telemetry, and experiment output.
- `/mnt/nvme/projects/` for active project checkouts and working trees.

Repository directories with the same names are for tracked metadata, notes, manifests, and small canonical examples only.

## Working Rules

- Do not install Isaac Sim until the Phase 2 plan is approved.
- Do not add ROS 2 yet.
- Prefer Docker-first workflows when the task is repeatable.
- Keep changes small and documented.
- Never make destructive changes without asking.
- Never commit or push unless explicitly instructed.
