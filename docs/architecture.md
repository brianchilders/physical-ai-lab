# Architecture

The repository is organized around a simple rule: source code, documentation, and repeatable configuration live in git, while heavy simulator assets, datasets, and caches live on NVMe.

## High-Level Model

```text
Git repo
  -> documentation
  -> config templates
  -> experiment definitions
  -> notebook analysis
  -> small canonical assets and examples

/mnt/nvme
  -> simulator installs
  -> caches
  -> large assets
  -> datasets
  -> logs
  -> active project worktrees
```

## Why Docker First

Docker is the preferred deployment boundary because it gives:

- reproducible environments
- explicit dependency control
- easy rollback and parallel experimentation
- a clean host/container split
- a natural place to document mounts, versions, and runtime assumptions

For Isaac Sim specifically, Docker keeps the simulator environment isolated from the host while still allowing NVIDIA GPU passthrough and direct access to host storage.

## Storage Architecture

The canonical local storage layout is:

```text
/mnt/nvme/
├── isaac/
├── cache/
├── assets/
├── datasets/
├── logs/
└── projects/
```

Rules:

- keep Isaac Sim payloads under `/mnt/nvme/isaac/`
- keep caches off the system disk when possible
- keep datasets and logs out of git
- store reusable artifacts in `/mnt/nvme/assets/`
- keep active working trees and lab sandboxes in `/mnt/nvme/projects/`

## Future ROS 2 Integration

ROS 2 is intentionally deferred for Phase 1. When introduced, it should sit beside Isaac Sim rather than inside the same undifferentiated setup.

Expected structure later:

- ROS 2 packages and workspaces live in dedicated project folders
- bridge nodes and adapters are isolated from simulator-only code
- simulator launch, sensor emulation, and ROS graph bring-up are documented as separate steps
- message contracts, topic maps, and launch files are versioned explicitly

## DGX Spark Integration

DGX Spark will eventually serve as a remote inference and compute tier.

Likely responsibilities:

- serving local LLMs
- running heavier vision-language workloads
- hosting shared models or model caches
- supporting distributed experiment workflows

Integration principle:

- the workstation remains the primary interactive development environment
- DGX Spark is called through documented network services, not ad hoc scripts
- inference endpoints, auth, and model versions are tracked in config and docs

## Phase Boundaries

Phase 1 defines the rules.

Phase 2 will add the first executable simulator container and validate the mount and runtime contract.
