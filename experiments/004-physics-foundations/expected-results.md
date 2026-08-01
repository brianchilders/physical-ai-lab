# Expected Results

Phase 6 produced a minimal but fully instrumented rigid-body simulation:

- a canonical authored stage in `output/`
- two clean run outputs in `output/run-01/` and `output/run-02/`
- two run summaries in `results/run-01/summary.json` and `results/run-02/summary.json`
- two per-step CSV traces in `results/run-01/step_metrics.csv` and `results/run-02/step_metrics.csv`
- a comparison report in `results/comparison.json` and `results/comparison.csv`
- a read-only inspection record in `results/summary.md`

## Expected Scene Behavior

- the stage default prim is `/World`
- the stage up-axis is `Z`
- meters-per-unit is `1.0`
- gravity is explicitly authored as `(0, 0, -9.81)`
- Isaac Sim 6.0.1 exposes the solver and broadphase generated tokens as `PhysxSchema.Tokens.TGS` and `PhysxSchema.Tokens.MBP`
- the canonical stage binds physics materials with the explicit relationship name `material:binding:physics` because `UsdShade.Tokens.physics` is not exposed by the installed bindings
- the authoring target uses `nvcr.io/nvidia/isaac-sim:6.0.1`
- the scene-authoring process may exit through a one-shot containment path after successful authoring and verification if `SimulationApp.close()` reproduces `Assertion (empty()) failed: Destroying busy TaskGroup!`
- that containment path is confined to `create_physics_scene.py` and does not authorize the same workaround for simulation, inspection, or comparison
- the read-only formal inspector also uses a narrow one-shot success containment path after all validation and hash checks complete because Isaac Sim 6.0.1 reproduces the same native Kit teardown defect after successful inspection
- the inspector-only workaround flushes validated artifacts before termination and does not apply to the simulation runner or any long-running Isaac Sim service, which should continue using the supported lifecycle
- during simulation, PhysX runtime state is authoritative for acceptance decisions; authored USD rigid-body velocities are preserved only as `usd_sampled_*` diagnostics and may become stale after a body sleeps
- the solver and broadphase tokens are `PhysxSchema.Tokens.TGS` and `PhysxSchema.Tokens.MBP`, with the lowercase variants unavailable in the installed Isaac Sim 6.0.1 bindings
- angular speed is the direct magnitude of angular velocity in `rad/s`, not a timestep-normalized quantity
- the ground collider remains static
- the cube slows due to friction and settles
- the sphere rebounds at least once due to restitution
- the simulation runs with a fixed `60 Hz` step
- the simulation stops within the bounded duration

## Expected Measurements

The two clean runs must agree within the following tolerances:

- final position: `<= 1 mm`
- final velocity: `<= 1 mm/s`
- rebound height: `<= 5 mm`
- settle step: `<= 1 simulation step`
- contact step: `<= 1 simulation step`
- orientation, angular velocity, angular speed, energy, and simulation time are compared with explicit documented tolerances in the generated comparison report

If a tolerance is exceeded, the comparison must report the first divergent field and step.

## Expected Metrics

Each body trace records:

- position
- sampled linear velocity
- authored `usd_sampled_*` linear velocity
- live runtime linear velocity
- pose-derived linear velocity
- authored `usd_sampled_*` angular velocity
- live runtime angular velocity
- rigid-body sleep state
- contact events
- kinetic energy
- gravitational potential energy
- total mechanical energy
- cube, sphere, and run settle-step markers
- canonical stage hashes
- inspection result
- comparison result
- maximum observed physics difference
- the normalized `contact_unknown` event counts, with the caveat that raw callback enum identifiers were not persisted

The failure diagnostics also report final-window ranges for authored `usd_sampled_*`, runtime, and pose-derived velocities, along with the per-step displacement range and discrepancy flags that separate stale authored state from live runtime state.

## Expected Console Markers

Authoring:

- `PHYSICS: SimulationApp initialized`
- `PHYSICS: world metadata authored`
- `PHYSICS: physics scene authored`
- `PHYSICS: canonical stage saved`
- `PHYSICS: requesting immediate shutdown`

Simulation:

- `PHYSICS: run-01 started`
- `PHYSICS: run-01 complete`
- `PHYSICS: run-02 started`
- `PHYSICS: run-02 complete`
- `PHYSICS: two clean runs completed`
- `PHYSICS: requesting immediate shutdown`

Inspection:

- `PHYSICS_INSPECT: root stage opened`
- `PHYSICS_INSPECT: run results opened`
- `PHYSICS_INSPECT: world metadata validated`
- `PHYSICS_INSPECT: hierarchy validated`
- `PHYSICS_INSPECT: inspection passed`

Comparison:

- `PHYSICS_COMPARE: run-01 summary opened`
- `PHYSICS_COMPARE: run-02 summary opened`
- `PHYSICS_COMPARE: tolerances validated`
- `PHYSICS_COMPARE: comparison passed`

## Phase 6 Completion

- scene authoring complete
- controlled simulation complete
- independent formal inspection complete
- cross-run reproducibility comparison complete
- Phase 6 overall complete

## Failure Conditions

- missing physics scene metadata
- missing collision or rigid-body schema
- missing explicit mass or physics material values
- missing contact report events
- missing rebound event for the sphere
- cube not settling within the bounded duration
- run-to-run differences beyond tolerance
- missing or malformed CSV/JSON traces
- any new external dependency or asset source
