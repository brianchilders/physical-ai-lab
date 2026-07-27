# Lab Status

## Validated Hardware

- Ubuntu 24.04.4 LTS workstation validated
- NVIDIA TITAN RTX 24 GB validated
- NVMe storage available at `/mnt/nvme`

## Validated Software

- NVIDIA driver validated
- Docker validated
- Docker GPU passthrough validated
- Vulkan validated

## Completed Milestones

- Phase 1 repository foundation complete
- Documentation-first structure established
- Canonical storage policy established
- Isaac Sim deployment scaffolding added to the repository

## Current Phase

Phase 2, deployment infrastructure in place and image download pending.

## Pending Work

- Isaac Sim image not yet pulled
- Isaac Sim not yet launched
- ROS 2 integration deferred
- DGX Spark integration deferred
- Phase 3 experiment harnesses not started

## Known Limitations

- GUI mode is local-display only
- remote work is expected to use SSH and headless launch paths
- TITAN RTX is practical but not the newest GPU tier in current NVIDIA docs
- Isaac Sim launch still depends on a future image download
- local GUI is optional and may require X11 authorization
- remote viewing is expected through headless livestreaming ports, not through normal SSH GUI forwarding

## Next Milestone

Finalize the Phase 2 deployment contract and begin Phase 3 experiment harness design.
