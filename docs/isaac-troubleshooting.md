# Isaac Sim Troubleshooting

This document covers the most likely Phase 2 failure modes.

## Storage Root Missing

Symptoms:

- `prepare-storage.sh` fails
- validation reports `/mnt/nvme` missing or unmounted

Fix:

- confirm `/mnt/nvme` is mounted
- rerun `./prepare-storage.sh`

## Required Directories Missing

Symptoms:

- launch wrappers stop immediately
- validation reports missing directories under `/mnt/nvme/isaac/`

Fix:

- run `./prepare-storage.sh`
- do not create alternate storage paths

## Bind Mount Not Writable

Symptoms:

- launch wrapper fails before the container starts
- a required storage directory exists but cannot be written to by the host user

Fix:

- verify the storage tree ownership and permissions on `/mnt/nvme/isaac`
- keep the container UID and GID aligned with the supported Isaac Sim `1234:1234` identity
- realign the dedicated runtime directories with `sudo make prepare-runtime-ownership CONFIRM_CHOWN=1` before retrying the launch

## Docker Daemon Down

Symptoms:

- `docker info` fails
- validation reports Docker daemon unreachable

Fix:

- start the Docker service outside the repo
- rerun validation

## NVIDIA Runtime Missing

Symptoms:

- validation reports the NVIDIA Docker runtime is not configured
- GPU passthrough fails

Fix:

- correct the host Docker GPU configuration outside the repo
- rerun validation

## Image Not Present

Symptoms:

- `launch-headless.sh` or `launch-gui.sh` reports the Isaac Sim image is missing locally

Fix:

- use the guarded `make pull-image CONFIRM_PULL=1` target for the pinned image
- if an anonymous pull fails with an authentication, authorization, locked-content, or license-acceptance error, accept the relevant NGC terms in the browser and then authenticate with the manual NGC workflow
- do not change the repo scripts to pull automatically

## First Launch Completed, Teardown Needs Work

Symptoms:

- the first smoke-test run reaches frame execution and then fails during shutdown
- a post-close segmentation fault appears after `SimulationApp.close()`

Fix:

- use the recorded immediate-shutdown smoke-test path in `experiments/001-first-launch/smoke_test.py`
- keep the successful fast-shutdown workaround documented in the experiment summary
- do not reintroduce the original graceful-close path unless the simulator teardown contract changes

## Compatibility Checker Fails

Symptoms:

- the built-in Isaac Sim compatibility checker reports a failure
- the first launch aborts before the simulator starts

Fix:

- treat the TITAN RTX as experimental because it is below NVIDIA's current RTX 4080 minimum reference
- resolve host driver, Vulkan, or container issues before attempting the first launch again
- rerun the compatibility checker before any simulator launch

## GUI Launch Fails

Symptoms:

- container starts but no window appears
- X11 or Vulkan errors appear in the logs

Likely causes:

- no local display
- `DISPLAY` not set correctly
- Xauthority access not available
- the session is remote rather than local

Fix:

- use headless mode on remote hosts
- use GUI mode only from a real desktop session
- do not expect SSH X-forwarding to provide a full Isaac Sim GUI experience

## Remote Viewing Ports

Symptoms:

- headless launch is ready but the client cannot connect

Check:

- WebRTC signaling should use `49100/tcp`
- WebRTC media should use `47998/udp`

The repository documents the ports only. It does not open firewall rules or change network configuration.

## Vulkan Errors

Symptoms:

- validation fails on `vulkaninfo`
- GUI launch aborts during graphics initialization

Fix:

- verify the host Vulkan stack outside the repo
- rerun validation before trying again

## GPU Memory Pressure

Symptoms:

- the simulator launches but scenes fail or become unstable
- complex scenarios use too much VRAM

Fix:

- reduce scene complexity
- reduce sensor count or resolution
- treat TITAN RTX capacity as a finite budget

## Future NGC Login or Terms Issues

Symptoms:

- a later manual pull fails with a license or acceptance error

Fix:

- accept the NVIDIA terms in the browser for the relevant NGC account
- keep the repo free of login automation
- use `$oauthtoken` with an NGC API key for the manual `docker login nvcr.io` step only if the guarded anonymous pull is denied
