# Phase 3 Summary

- Date: 2026-07-27
- Image: `nvcr.io/nvidia/isaac-sim:6.0.1`
- Digest: `sha256:783444c706538aa76cf5126e911ddc5e618779e6105305ad4af4260362a30aa9`
- Host GPU: NVIDIA TITAN RTX 24 GB
- Host driver: 595.84
- Compatibility checker: PASS
- Headless launch: PASS
- Smoke-test frames: 10/10
- Peak GPU memory: 1572 MiB
- Shutdown method: `app.close(skip_cleanup=True, exit_code=exit_code)`
- Final smoke exit code: `0`
- Known graceful-teardown issue: the original smoke-test shutdown path reached `SimulationApp.close()` and then terminated with a post-close segmentation fault
- Successful workaround: removing `fast_shutdown=False` and using the immediate-shutdown close path preserved a clean exit
- Final Phase 3 status: complete

Notes:

- The first failed teardown and its raw logs are preserved in the experiment record but are not staged here.
- The healthy headless service remained running during the smoke-test work.
- This summary intentionally omits raw logs, container IDs, device UUIDs, private addresses, tokens, and secrets.
