# Isaac Sim Validation

This phase adds validation tooling only. Nothing here modifies the workstation.

## What Is Checked

The validation scripts verify:

- Ubuntu release
- kernel version
- architecture
- local versus SSH session
- NVIDIA driver presence
- GPU visibility
- GPU memory reporting
- Docker CLI availability
- Docker daemon health
- NVIDIA Docker runtime presence
- Docker GPU passthrough, when a local test image is available
- Vulkan availability and basic health
- system RAM
- available NVMe storage
- required `/mnt/nvme/isaac/` directory structure
- pinned Isaac Sim image reference resolution
- canonical Compose file presence

Additional helper checks are available as lightweight tests:

- `make config-check`
- `make compose-check`
- `make image-status`

## Commands

```bash
./prepare-storage.sh
./validate-workstation.sh
```

`prepare-storage.sh` is safe to rerun. It only creates directories and reports free space.

## Output Format

Validation output uses one of three states:

- `PASS` for verified good conditions
- `WARN` for incomplete but non-fatal checks
- `FAIL` for conditions that block the Phase 2 deployment path

The script exits non-zero if any `FAIL` is recorded.

## GPU Passthrough Check

The passthrough check only runs when a suitable local container image is already present.

This is intentional:

- no large image pulls
- no login automation
- no workstation modifications

If no local image exists, the script warns instead of forcing a download.

The validation path does not install software, start a simulator container, or modify network settings.

The container-level GPU smoke test is reported as `Container GPU readiness` because it verifies Docker GPU passthrough only.
`Isaac runtime readiness` is reserved for the phase where the simulator itself actually starts.

## Headless Vulkan

Headless validation deliberately removes graphical session variables before invoking `vulkaninfo`.
That keeps SSH-based validation independent from local X11 or Wayland state.

If a local desktop session is present, the validator can report optional surface information separately.
GUI mode remains a local-session path and is not advertised for ordinary SSH use.

## Recommended Readout

Before a launch, you want to see:

- `PASS` on Ubuntu 24.04
- `PASS` on x86_64
- `PASS` on NVIDIA driver visibility
- `PASS` on Docker daemon and NVIDIA runtime
- `PASS` on Vulkan
- `PASS` on `/mnt/nvme/isaac/`

Any `FAIL` should be resolved before attempting an Isaac Sim launch.
