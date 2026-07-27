# First Launch Smoke Test

This experiment records the smallest reproducible Isaac Sim Python smoke test for the first successful headless launch milestone.

## Goals

- verify the Isaac Sim Python runtime starts
- initialize `SimulationApp` headlessly
- create an empty stage
- advance a few frames
- close cleanly

The first shutdown attempt exposed a teardown bug after `SimulationApp.close()`. The preserved smoke-test record therefore includes both the original graceful-close failure and the successful immediate-shutdown workaround.

## Constraints

- no external assets
- no ROS 2
- no GUI mode
- no livestream setup
- no repository writes from inside the container

## Runtime

The smoke test uses a dedicated runtime root under:

`/mnt/nvme/isaac/smoke/001-first-launch/`

The run log is captured on the host under `results/`.

## Recorded Outcome

- Image: `nvcr.io/nvidia/isaac-sim:6.0.1`
- Digest: `sha256:783444c706538aa76cf5126e911ddc5e618779e6105305ad4af4260362a30aa9`
- Frames completed: 10/10
- Peak GPU memory observed: 1572 MiB
- Final smoke exit code: `0`
- Shutdown workaround: `app.close(skip_cleanup=True, exit_code=exit_code)`
