# Lab Status

## Validated Hardware

- Ubuntu 24.04.4 LTS workstation validated
- NVIDIA TITAN RTX 24 GB validated
- NVMe storage available at `/mnt/nvme`
- Docker daemon root at `/mnt/nvme/docker-data`
- Available NVMe space is sufficient for the pinned Isaac Sim image and initial cache growth

## Validated Software

- NVIDIA driver validated
- Docker validated
- Docker GPU passthrough validated
- Vulkan validated
- runtime defaults set to supported Isaac Sim user `1234:1234`

## Completed Milestones

- Phase 1 repository foundation complete
- Documentation-first structure established
- Canonical storage policy established
- Isaac Sim deployment scaffolding added to the repository
- Phase 3 first successful headless Isaac Sim launch complete
- Minimal Python smoke test complete with immediate-shutdown teardown fix
- Lifecycle stop path validated with the headless Compose profile
- Phase 4A OpenUSD stage authoring complete
- Phase 4B OpenUSD scene inspection complete
- Phase 4 overall complete
- Phase 5 USD composition foundations complete
- Phase 6 physics foundations complete

## Current Phase

Phase 4 complete. Phase 5 is complete. Phase 6 physics foundations is complete.

## Pending Work

- ROS 2 integration deferred
- DGX Spark integration deferred
- Phase 7 interactive Isaac Sim development environment planning pending

## Known Limitations

- GUI mode is local-display only
- remote work is expected to use SSH and headless launch paths
- TITAN RTX is below NVIDIA's current RTX 4080 minimum reference and should be treated as experimental
- Isaac Sim phase 3 is complete, but the TITAN RTX remains an experimental platform relative to NVIDIA's current RTX 4080 minimum reference
- local GUI is optional and may require X11 authorization
- remote viewing is expected through headless livestreaming ports, not through normal SSH GUI forwarding
- `PRIVACY_CONSENT` defaults to `N` unless explicitly enabled
- the approved runtime ownership prep target is guarded and limited to the dedicated Isaac directories only
- the smoke-test teardown path now uses immediate shutdown to avoid the post-close segmentation fault seen in the first attempt
- `make stop` requires the headless Compose profile to remove the project cleanly
- Phase 5 composition work is complete and now provides the wrapper-stage foundation for future real-world environment ingestion such as OVER USDZ captures

## Next Milestone

Begin Phase 7 interactive Isaac Sim development environment planning.
