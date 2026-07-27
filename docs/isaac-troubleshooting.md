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

- download the approved image later using the official NVIDIA workflow
- do not change the repo scripts to pull automatically

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
