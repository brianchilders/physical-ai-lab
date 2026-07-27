# Isaac Sim Docker

This directory documents the Isaac Sim container boundary used by Phase 2.

Design intent:

- use Docker as the runtime boundary
- keep host dependencies minimal
- isolate Isaac Sim-specific packages, caches, and runtime state
- mount large data from `/mnt/nvme/isaac/` instead of baking it into images
- keep the launch contract reproducible and documented
- keep the canonical Compose file at [docker/isaac/compose.yaml](compose.yaml)
- keep the pinned image reference data-driven through registry, repository, and tag variables

Selected image:

- `nvcr.io/nvidia/isaac-sim:6.0.1`

Why this image:

- it matches the current official NVIDIA Isaac Sim container documentation
- it is the current documented NGC registry target
- it keeps the repo aligned with supported launch guidance

This directory does not install Isaac Sim and does not automate downloads.

Expected responsibilities:

- host/container mount documentation
- launch wrapper notes
- validation notes
- version and environment variable conventions
- future extension for web viewer or additional runtime variants

Launch strategy:

- headless is the primary supported path for SSH-driven use
- GUI is optional and intended only for a real local desktop session
- livestreaming uses Isaac Sim network ports, but this repository does not open firewall rules or manage network policy
- no Docker socket mount and no privileged container mode are used

Planned mount points beneath the canonical storage root:

- `/mnt/nvme/isaac/cache/`
- `/mnt/nvme/isaac/assets/`
- `/mnt/nvme/isaac/datasets/`
- `/mnt/nvme/isaac/logs/`
- `/mnt/nvme/isaac/projects/`
