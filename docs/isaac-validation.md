# Isaac Sim Validation

This phase adds validation tooling for the Isaac Sim deployment and first-launch contract. Nothing here modifies the workstation.

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
- `make pull-image CONFIRM_PULL=1`
- `make validate-runtime-ownership`
- `make validate-usd-composition-ownership`

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

Before any launch, the launch wrapper checks that each required bind-mounted directory is writable by creating and removing a temporary file.

If the runtime directories need to be realigned, use the guarded ownership target:

```bash
sudo make prepare-runtime-ownership CONFIRM_CHOWN=1
```

The read-only ownership validation target checks that the supported `1234:1234` identity can write the approved Isaac runtime paths and reports the current ownership of `assets` and `datasets` without changing them. Numeric ownership must be validated from the normal host shell; if a namespace-obscured environment reports `65534:65534`, treat that as `NOT TESTED` for host ownership, not as a pass and not as a reason to mutate ownership. Container effective-access probes are separate from host numeric ownership checks.

Phase 5 adds a separate USD composition ownership and validation path under
`/mnt/nvme/isaac/experiments/003-usd-composition/`. The static validation target
does not launch Isaac Sim, but it still uses a short-lived container to verify
the mounted Phase 5 paths are owned by the supported `1234:1234` identity.

The independent Phase 5 composition inspector is a disposable read-only
validator. It performs immutable stage inspection inside the Isaac Sim Python
environment, prints its validation markers, and terminates with `os._exit()`
instead of calling `SimulationApp.close()`. That workaround is scoped only to
the one-shot inspector container because Isaac Sim 6.0.1 exhibited teardown
defects after successful validation. Normal authoring scripts and long-lived
services should continue to use the validated shutdown path.

Phase 7 adds a separate Interactive Studio launch and ownership validation
path. It remains launch-prerequisite validation only and does not start Isaac
Sim during the prelaunch checks. The Interactive Studio ownership validator
must be run from the normal host shell when host numeric ownership is being
verified; if a namespace-obscured environment reports `65534:65534`, treat that
result as `NOT TESTED` rather than a pass. Container effective-access probes
are separate from host numeric ownership checks.

For the headless launch, host port availability should be checked before start-up for:

- `49100/tcp`
- `47998/udp`

Once the pinned image is present locally, the container's built-in compatibility checker must run before the first Isaac Sim launch.

After a successful pull, record the local image digest with `docker image inspect` before the launch step.

The container-level GPU smoke test is reported as `Container GPU readiness` because it verifies Docker GPU passthrough only.
It prefers locally installed CUDA images and may fall back to the pinned Isaac Sim image only with an explicit `nvidia-smi` entrypoint when no CUDA image is present.

`Isaac runtime readiness` is reported separately and is marked `HISTORICAL` when the repository already contains a recorded successful headless launch and smoke test. It is not the same thing as the generic GPU passthrough check.

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
- a recorded local image digest from `docker image inspect`
- a compatibility-check pass from the container image before the first launch

Any `FAIL` should be resolved before attempting an Isaac Sim launch. When the Phase 3 records already show a successful headless launch and smoke test, focus on preserving that state rather than relaunching to “prove” history again.
