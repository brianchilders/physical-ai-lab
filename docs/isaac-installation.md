# Isaac Sim Installation

Phase 2 prepares a reproducible Isaac Sim deployment boundary without installing Isaac Sim yet.

## Selected Version

- Image: `nvcr.io/nvidia/isaac-sim:6.0.1`
- Registry: `nvcr.io`
- Repository: `nvidia/isaac-sim`
- Tag: `6.0.1`

This version is selected because the current official NVIDIA Isaac Sim container documentation points to `6.0.1` as the current container target and uses NGC-hosted images for the documented container workflow.

The pinned image resolves to `nvcr.io/nvidia/isaac-sim:6.0.1`.

The version is configured in:

- [config/lab.env.example](../config/lab.env.example)
- [docker/isaac/compose.yaml](../docker/isaac/compose.yaml)
- [launch-headless.sh](../launch-headless.sh)
- [launch-gui.sh](../launch-gui.sh)
- [tests/phase2-refinement.sh](../tests/phase2-refinement.sh)

Update it by changing `config/lab.env.example` first, then validating the Compose render and local launch wrappers together. Do not switch to `latest`.

## Why Docker

Docker is the deployment boundary for this phase because it keeps host dependencies small, isolates simulator state, and gives us a reproducible launch contract.

Using Docker also keeps the host workstation aligned with official Isaac Sim container guidance and makes image upgrades explicit rather than ad hoc.

The supported container identity is `1234:1234`, matching the official Isaac Sim 6.0.1 container contract.

The Docker daemon root is `/mnt/nvme/docker-data`, which sits on the same NVMe filesystem as `/mnt/nvme/isaac`. The available space on that filesystem is sufficient for the pinned Isaac Sim image and initial cache growth.

## Storage Contract

All Isaac Sim-related data stays beneath `/mnt/nvme/isaac/`.

Required layout:

```text
/mnt/nvme/isaac/
├── cache/
│   ├── isaac-sim/
│   │   ├── computecache/
│   │   └── main/
│   └── ov/
│       └── hub/
├── assets/
├── datasets/
├── logs/
│   └── isaac-sim/
└── projects/
    └── isaac-sim/
        ├── config/
        ├── data/
        └── pkg/
```

`prepare-storage.sh` creates this tree idempotently and does not delete anything.

Mount review against the official container guidance:

- persistent host data stays beneath `/mnt/nvme/isaac`
- cache, logs, config, data, assets, datasets, and package state are separated
- no Docker socket is mounted
- privileged mode is not used
- the canonical mounts are duplicated only once in Compose, not in each launch script
- user ID and group ID default to the host user and group so bind mounts stay writable unless explicitly overridden
- `assets` and `datasets` mounts are lab-specific additions, not required by NVIDIA's minimal example, but they remain inside the canonical storage root
- the container user defaults remain `1234:1234` to match the supported Isaac Sim runtime contract

The first image pull and launch should record the local digest with `docker image inspect` after the pull completes.

Recommended digest capture command:

```bash
docker image inspect --format '{{index .RepoDigests 0}}' nvcr.io/nvidia/isaac-sim:6.0.1
```

## Launch Modes

### Headless

Use `./launch-headless.sh` for the simulator runtime path that is intended for livestreaming and future automation.

This is the primary supported mode for the workstation because SSH is the normal access path.

### GUI

Use `./launch-gui.sh` only on a real local desktop session with a visible display.

GUI mode does not automate display authorization. If your workstation requires `xhost` access for local containers, grant that separately before launch.

GUI mode is optional. It is not the supported path for a normal SSH session.

### Livestreaming

Headless mode is the base for native Isaac Sim livestream clients.

Documented streaming ports:

- `49100/tcp` for WebRTC signaling
- `47998/udp` for WebRTC media

This repository documents the ports but does not open firewall rules or alter network policy.

### Web Viewer

The official NVIDIA docs describe a Docker Compose web viewer deployment path, but this repository does not implement that viewer yet. Phase 2 keeps the launch contract focused on headless and local GUI support.

### Validation

Use `./validate-workstation.sh` to check the host, GPU, Docker runtime, Vulkan, and storage layout before attempting a launch.

## Authentication

Do not automate `docker login`.

The guarded repository pull target first attempts an anonymous pull of `nvcr.io/nvidia/isaac-sim:6.0.1`. If that returns an authentication, authorization, locked-content, or license-acceptance error, the next step is manual NGC authentication outside the repository.

Compose files and wrapper scripts do not perform `docker login` or `docker pull`.

`PRIVACY_CONSENT` now defaults to `N` so privacy consent is opt-out unless you explicitly choose to opt in for a later run.

When the dedicated Isaac runtime directories need to be aligned to the supported container identity, use:

```bash
sudo make prepare-runtime-ownership CONFIRM_CHOWN=1
```

That guarded target only touches the approved Isaac runtime paths listed in this document and leaves `/mnt/nvme/docker-data`, `/mnt/nvme/isaac`, `assets`, and `datasets` untouched.

Before the first Isaac Sim launch, run the container's built-in compatibility checker after the image is present locally. That check should happen before any headless or GUI launch.

Recommended compatibility-check command:

```bash
docker run --entrypoint bash -it --gpus all --rm --network=host \
  nvcr.io/nvidia/isaac-sim:6.0.1 \
  ./isaac-sim.compatibility_check.sh --/app/quitAfter=10 --no-window
```

## Update Strategy

When NVIDIA publishes a newer supported image, update:

1. `config/lab.env.example`
2. `docker/isaac/compose.yaml`
3. launch scripts
4. this document
5. troubleshooting notes if the launch contract changes

The version bump should happen as a deliberate change after validating compatibility with the workstation.

## TITAN RTX Notes

The TITAN RTX has RT cores and 24 GB of VRAM, which is a good fit for local Isaac Sim work.

Compatibility considerations:

- NVIDIA's current NGC catalog references a minimum local GPU class of RTX 4080 or higher
- TITAN RTX is therefore below the current official minimum reference and should be treated as experimental
- complex scenes, many RTX sensors, and future Isaac Lab workloads may push VRAM limits

The practical risk is workload size, not basic GPU class support.

## References

- [Isaac Sim container installation](https://docs.isaacsim.omniverse.nvidia.com/latest/installation/install_container.html)
- [Isaac Sim requirements](https://docs.isaacsim.omniverse.nvidia.com/latest/installation/requirements.html)
- [Isaac Sim setup tips](https://docs.isaacsim.omniverse.nvidia.com/latest/installation/install_faq.html)
