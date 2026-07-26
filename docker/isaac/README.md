# Isaac Sim Docker

This directory is reserved for the Isaac Sim container boundary.

Phase 1 does not install Isaac Sim. The goal here is to define the contract that will make installation reproducible later.

Design intent:

- use Docker as the main runtime boundary
- keep host dependencies minimal
- isolate Isaac Sim-specific packages, caches, and runtime state
- mount large data from `/mnt/nvme` instead of baking it into images

Expected future responsibilities:

- base image and runtime image definitions
- launch wrappers
- GPU and Vulkan validation notes
- volume mount documentation
- simulator-specific environment files

Planned mount points:

- `/mnt/nvme/isaac/`
- `/mnt/nvme/cache/`
- `/mnt/nvme/assets/`
- `/mnt/nvme/datasets/`
- `/mnt/nvme/logs/`
