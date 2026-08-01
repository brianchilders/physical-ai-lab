# Physics Foundations

Phase 6 is the deterministic physics foundation lab for the Physical AI Lab.

This phase stays intentionally small and reproducible:

- one physics scene
- one static ground collider
- one low-bounce cube
- one high-bounce sphere
- explicit collision and rigid-body schemas
- explicit mass and physics materials
- fixed-step simulation
- bounded simulation duration
- contact and rebound detection
- two clean runs
- reproducibility comparison
- independent read-only inspection

The phase deliberately excludes:

- robots
- joints
- articulations
- controllers
- sensors
- ROS 2
- Isaac Lab
- reinforcement learning
- external assets
- network downloads
- OVER or USDZ
- DGX Spark integration

## Responsibilities

- `create_physics_scene.py` authors the canonical stage and world metadata.
- `run_physics_experiment.py` executes two clean simulation runs and records traces.
- `inspect_physics_results.py` performs immutable read-only inspection of the generated stage and result files.
- `compare_physics_runs.py` compares the two runs with explicit tolerances.

Isaac Sim 6.0.1 exposes the generated PhysX solver and broadphase members as `PhysxSchema.Tokens.TGS` and `PhysxSchema.Tokens.MBP`.
The runtime bindings do not expose `UsdShade.Tokens.physics`, so the canonical stage binds physics materials with the explicit relationship name `material:binding:physics`.
Scene authoring uses the Isaac Sim image `nvcr.io/nvidia/isaac-sim:6.0.1` and contains a narrow one-shot shutdown containment path because the supported `SimulationApp.close()` path reproduces `Assertion (empty()) failed: Destroying busy TaskGroup!` after successful stage authoring and verification.
This containment path is limited to `create_physics_scene.py` and does not authorize the same workaround for simulation, inspection, or comparison scripts.
The formal read-only inspector now uses its own one-shot success containment path after all validation and hash checks complete, because Isaac Sim 6.0.1 reproduces the same native Kit teardown defect after successful inspection. The inspector-only workaround flushes validated artifacts before termination and does not apply to the simulation runner or any long-running Isaac Sim service, which should continue using the supported lifecycle.
During simulation, PhysX runtime state is authoritative for pass/fail decisions. Authored USD rigid-body velocity attributes are retained only as `usd_sampled_*` diagnostics and may remain stale after a body sleeps; they are not used for settlement, rebound qualification, or energy acceptance.

Phase 6 completed all four milestones:

- scene authoring
- controlled simulation
- independent formal inspection
- cross-run reproducibility comparison

Technical lessons from the phase:

- Isaac Sim 6.0.1 exposes `PhysxSchema.Tokens.TGS` and `PhysxSchema.Tokens.MBP`; the lowercase variants are not available in the installed bindings.
- Live PhysX runtime state is authoritative during simulation; authored USD velocities are diagnostics only, pose-derived velocity is a cross-check, and sleep state is tracked separately through PhysX.
- Angular speed is the direct magnitude of angular velocity in `rad/s`; it is not divided by timestep or simulation frequency.
- The teardown containment scope is deliberately narrow: `create_physics_scene.py` and `inspect_physics_results.py` use one-shot success containment after verified completion, while `run_physics_experiment.py` uses the supported shutdown path and does not call `os._exit()`.
- Required contact-found and contact-lost outcomes were validated, but the normalized `contact_unknown` counts cannot be mapped back to raw callback enum integers because those raw identifiers were not persisted.

## File Layout

Tracked source files:

- `create_physics_scene.py`
- `run_physics_experiment.py`
- `inspect_physics_results.py`
- `compare_physics_runs.py`
- `expected-results.md`
- `expected-hierarchy.txt`
- `results/summary.md`

Generated runtime files live under:

- `/mnt/nvme/isaac/experiments/004-physics-foundations/output`
- `/mnt/nvme/isaac/experiments/004-physics-foundations/results`

## How To Run

Prepare the runtime directories:

```bash
make prepare-physics-foundations
```

Prepare ownership only when explicitly approved:

```bash
sudo make prepare-physics-foundations-ownership CONFIRM_CHOWN=1
```

Validate ownership from a short-lived container:

```bash
make validate-physics-foundations-ownership
```

Author the canonical stage:

```bash
make create-physics-scene
```

Run the two clean simulations:

```bash
make run-physics-experiment
```

Inspect the generated outputs in read-only mode:

```bash
make inspect-physics-results
```

Compare the two runs:

```bash
make compare-physics-runs
```

Run the static refinement checks:

```bash
make test-phase6
```

## Expected Output

The authoring step writes a canonical scene file with explicit world metadata and physics schemas.

The experiment step writes two clean run directories with:

- CSV traces
- JSON summaries
- world metadata
- per-step kinematics
- authored `usd_sampled_*` velocity diagnostics, live-runtime velocity diagnostics, and pose-derived velocity diagnostics
- rigid-body sleep-state diagnostics
- contact events
- energy metrics
- angular speed computed as the magnitude of the live angular-velocity vector
- per-body settle-step markers for the cube, sphere, and overall run

The comparison step reports whether the runs match within the declared tolerances and pinpoints the first divergence when they do not.

## Cleanup

Generated `.usd`, `.usda`, `.csv`, `.json`, and `.log` files remain ignored by git. Remove them manually if you want a fresh run; the repository does not prune them automatically.
