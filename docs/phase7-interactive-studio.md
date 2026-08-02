# Phase 7 - Interactive Studio

Status: complete

Phase 7 adds an interactive execution environment that is intentionally separate from the Phase 6 production runtime.

## Architecture

The lab now has three distinct layers:

- Production Runtime
- Interactive Studio
- Shared Assets

Production Runtime remains deterministic, headless, disposable, and authoritative for reproducible experiments.

Interactive Studio is persistent, operator-driven, visually interactive, and intended for authoring, debugging, and future digital-twin workflows.

Shared Assets are curated reusable content that can be consumed by both execution tracks, but are not owned by either runtime.

## Storage Model

### Shared Assets

Conceptual root:

```text
/mnt/nvme/isaac/assets/
```

This tree is mounted read-only by default in Interactive Studio.

### Interactive Studio Runtime

Conceptual root:

```text
/mnt/nvme/isaac/interactive-studio/
```

Planned subtrees:

- `cache/main`
- `cache/computecache`
- `cache/hub`
- `config`
- `data`
- `logs`
- `pkg`
- `sessions`

### Interactive Workspace

Writable development workspace:

```text
/mnt/nvme/isaac/interactive-studio/workspace/
```

Planned subtrees:

- `projects`
- `working-scenes`
- `exports`
- `captures`
- `screenshots`
- `scratch`

## Container Model

The first release uses a dedicated persistent Docker wrapper rather than Docker Compose.

Planned container identity:

- container name: `interactive-studio`
- image: `nvcr.io/nvidia/isaac-sim:6.0.1`
- network: `host`
- shared memory: `16g`
- user: `1234:1234`
- restart policy: none in the first release

The launcher uses `exec ./runheadless.sh` inside the container shell so the Isaac Sim process replaces the shell where the pinned launcher allows it.
The command passes explicit primary-stream Kit settings:

```text
--/exts/omni.kit.livestream.app/primaryStream/publicIp
--/exts/omni.kit.livestream.app/primaryStream/signalPort
--/exts/omni.kit.livestream.app/primaryStream/streamPort
```

The wrapper keeps `INTERACTIVE_STUDIO_HOST_IP`, `INTERACTIVE_STUDIO_SIGNAL_PORT`, and `INTERACTIVE_STUDIO_STREAM_PORT` as user-facing configuration and translates them into those explicit Kit arguments.
The container does not rely on `ISAACSIM_HOST`, `ISAACSIM_SIGNAL_PORT`, or `ISAACSIM_STREAM_PORT` as authoritative configuration for the first release.

## Streaming Model

The Linux host runs Isaac Sim and exposes the supported WebRTC streaming workflow.

Planned connection model:

- Windows acts only as a remote client
- the supported Isaac Sim WebRTC Streaming Client is the baseline Windows client
- the Linux host IP is required explicitly through `INTERACTIVE_STUDIO_HOST_IP`
- signaling port: `49100/TCP`
- media port: `47998/UDP`

The explicit host IP requirement is intentional because the server may have multiple interfaces and the wrong address would make the streaming session unusable.

Readiness remains provisional until runtime validation against the pinned 6.0.1 logs confirms the exact candidate marker.
The current candidate marker is:

```text
Isaac Sim Full Streaming App is loaded.
```

Other 6.0.1 log markers may still be discovered at runtime and recorded later.

## Lifecycle

Interactive Studio uses a persistent container lifecycle.

Planned commands:

- prepare runtime directories
- prepare ownership
- validate ownership
- validate launch prerequisites
- start
- stop
- restart
- status
- logs
- shell

The container retained after a clean stop remains available until a later explicit cleanup decision is approved.
This means the container retained after a clean stop for the first release.
Persistence comes from the bind-mounted host paths, not from the container writable layer.

The approved baseline restart is an explicit operator action:

1. stop the exact `interactive-studio` container if it is running;
2. verify it is stopped;
3. remove only that exact stopped container;
4. recreate it with the canonical start configuration.

This is not broad cleanup and it does not apply to other containers.

Planned host preparation sequencing for the first release keeps root creation separate from ordinary preparation when `/mnt/nvme/isaac/interactive-studio` does not yet exist:

```text
sudo mkdir -p /mnt/nvme/isaac/interactive-studio
sudo chown <approved-root-owner> /mnt/nvme/isaac/interactive-studio
make prepare-interactive-studio
sudo make prepare-interactive-studio-ownership CONFIRM_CHOWN=1
make validate-interactive-studio-ownership
```

The scripts themselves never invoke `sudo`.

Workspace collaboration uses group `1000` with setgid directories in mode `2775` and a collaborative umask of `0002` so new files are not group-read-only by default.
Ownership validation uses a short-lived non-GPU probe container with the pinned image only for shell-based write checks; it does not start Isaac Sim.
Shared Assets are read-only.
Host numeric ownership validation must be run from the normal host shell. A namespace-obscured environment may report `65534:65534`; that result is `NOT TESTED` for host ownership and must not be treated as equivalent to `1234:1234` or used to relax the validator. Container effective-access probes are separate from host numeric ownership checks.

## Acceptance Result

The first Windows WebRTC connection and interactive authoring smoke test completed successfully.

Summary:

- Windows WebRTC connection succeeded
- interactive authoring succeeded
- workspace save succeeded
- lifecycle recreation and reconnect succeeded
- Phase 7 overall complete

Validated behaviors:

- Windows Isaac Sim WebRTC Streaming Client connected successfully to the pinned Linux host IP
- viewport rendering succeeded
- UI input and camera navigation succeeded
- interactive authoring succeeded
- scene save succeeded into the writable Interactive Workspace
- host-visible persistence succeeded
- collaborative ownership policy succeeded
- the Interactive Studio container remained running after the save
- the saved scene survived container stop, explicit recreation, and reconnect
- the scene reopened successfully after lifecycle recreation
- `/World/boxActor` remained visible and visually intact after reconnect

Final scene metadata:

- canonical scene path: `interactive-studio/workspace/working-scenes/phase7-interactive-smoke.usd`
- default prim: `/World`
- metersPerUnit: `0.01`
- upAxis: `Z`
- key prims: `/World/boxActor`, `/World/physicsScene`, `/World/roomScene`
- final SHA-256: `d92b7210a1cd015335b04e061878383bddd55604ad46dbdd9792caaf0d909680`

The saved smoke-test scene lives in the Interactive Workspace, not in the Git repository and not in Shared Assets.
Container restart and reconnect persistence remain a separate milestone.

## Hub Cache

The accidental cache-button action downloaded a persistent package at:

```text
/mnt/nvme/isaac/interactive-studio/pkg/hub-2.2.0
```

Current Hub status:

- Hub Workstation Cache downloaded as a persistent package but intentionally deferred
- Hub package version downloaded: `2.2.0`
- package location: `interactive-studio/pkg/hub-2.2.0`
- no Hub service or host container is active
- no Hub image was downloaded
- restart was intentionally deferred
- Interactive Studio does not depend on Hub activation for current operation
- future Hub evaluation should use a separately managed, explicitly approved service design

The package remains installed but inactive. Port `14090` is closed, no Hub host container exists, and no Hub image was downloaded.

## Security

The baseline assumes:

- trusted LAN or VPN only
- no public exposure
- no automatic firewall mutation
- no automatic image pulls
- no secrets in the runtime tree

## Phase Boundary

Interactive Studio does not replace the Phase 6 production runtime.

Phase 6 remains the authoritative experiment lane.
Interactive Studio is the operator-facing authoring and debugging lane.

## Lifecycle Note

The approved stop target retained the exact Interactive Studio container, but Docker stop ultimately returned exit code `137`. That indicates the container was forced down after the graceful stop timeout. Bind-mounted state and saved scenes remained intact, and the restart/reconnect sequence succeeded. This is a lifecycle hardening issue to address separately. It is not a graceful shutdown and it is not an argument for broad `os._exit()` containment in Interactive Studio.
