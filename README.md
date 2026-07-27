# Physical AI Lab

This repository is the long-term home for robotics, simulation, perception, AI inference, and experimentation across the Physical AI lab.

Phase 1 established the engineering foundation.

Phase 2 prepares the Isaac Sim deployment boundary:

- repository structure
- documentation-first workflow
- storage conventions for `/mnt/nvme/isaac`
- reproducible Isaac Sim Docker layout
- host validation and storage preparation scripts
- notebook, experiment, asset, and dataset organization
- roadmap and milestone tracking

Isaac Sim is not being installed yet. ROS 2 is intentionally deferred.

## Optional Developer Tools

The repository scripts are designed to work on a standard Ubuntu install without Ripgrep.
These tools are still useful during local development:

- `ripgrep` for fast ad hoc search
- `shellcheck` for shell linting

If they are not installed, the validation and refinement tests fall back to portable shell commands or skip the lint step.

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

- [Documentation Index](docs/README.md)
- [Project Vision](docs/vision.md)
- [Architecture](docs/architecture.md)
- [Storage Plan](docs/storage.md)
- [Development Workflow](docs/workflow.md)
- [Roadmap](docs/roadmap.md)
- [Milestones](docs/milestones.md)
- [Lab Status](docs/status.md)

## Phase Plan

1. Phase 1: platform foundation, documentation, and repository organization.
2. Phase 2: Isaac Sim deployment infrastructure, validation, and reproducible launch contract.
3. Phase 3: controlled first-launch validation, smoke-test harnesses, and experiment records.
4. Phase 4: OpenUSD foundations, stage authoring, and reusable scene inspection. Complete.
5. Phase 5: USD composition foundations, layer stacks, references, payloads, and wrapper stages. Complete.
6. Phase 6: Physics foundations, simulation configuration, and the next environment/robot integration layer.

## Storage Convention

The canonical storage root for Isaac Sim is `/mnt/nvme/isaac`.

- `/mnt/nvme/isaac/cache/` for simulator caches and Omniverse cache state.
- `/mnt/nvme/isaac/assets/` for reusable meshes, textures, calibration artifacts, and USD resources.
- `/mnt/nvme/isaac/datasets/` for raw and processed experiment data.
- `/mnt/nvme/isaac/logs/` for run logs, telemetry, and experiment output.
- `/mnt/nvme/isaac/projects/` for active project checkouts, working trees, and simulator runtime state.

Repository directories with the same names are for tracked metadata, notes, manifests, and small canonical examples only.

Phase 2 adds nested Isaac Sim runtime directories below that root:

- `/mnt/nvme/isaac/cache/isaac-sim/main`
- `/mnt/nvme/isaac/cache/isaac-sim/computecache`
- `/mnt/nvme/isaac/cache/ov/hub`
- `/mnt/nvme/isaac/logs/isaac-sim`
- `/mnt/nvme/isaac/projects/isaac-sim/config`
- `/mnt/nvme/isaac/projects/isaac-sim/data`
- `/mnt/nvme/isaac/projects/isaac-sim/pkg`

Configuration precedence is documented in [config/lab.env.example](config/lab.env.example) and follows:

1. shell environment variables
2. local `.env`
3. `.env.example`
4. `config/lab.env.example`

See:

- [Isaac Sim installation](docs/isaac-installation.md)
- [Isaac Sim validation](docs/isaac-validation.md)
- [Isaac Sim troubleshooting](docs/isaac-troubleshooting.md)

Phase 2 entry points:

- `./prepare-storage.sh`
- `./validate-workstation.sh`
- `./launch-headless.sh`
- `./launch-gui.sh`
- `./stop.sh`

Phase 3 first-launch artifacts live under `experiments/001-first-launch/` and record the initial successful headless launch, smoke test, and teardown behavior.

Phase 4 OpenUSD foundations artifacts live under `experiments/002-openusd-foundations/` and record the first reproducible stage-authoring and inspection lab.

The next milestone is Phase 6: Physics foundations.

Phase 5 established the USD composition model that will support future wrapper stages around real-world environments, OVER USDZ captures, robot assets, sensor rigs, and simulation configuration without redesigning the composition workflow.

## Working Rules

- Do not install Isaac Sim until the Phase 2 plan is approved.
- Do not add ROS 2 yet.
- Prefer Docker-first workflows when the task is repeatable.
- Keep changes small and documented.
- Never make destructive changes without asking.
- Never commit or push unless explicitly instructed.
