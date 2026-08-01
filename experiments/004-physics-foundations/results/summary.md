# Phase 6 Summary

Phase 6 is complete.

## Canonical Contract

- Isaac Sim image: `nvcr.io/nvidia/isaac-sim:6.0.1`
- Canonical hierarchy:
  - `/World`
  - `/World/PhysicsScene`
  - `/World/Looks`
  - `/World/Looks/GroundMaterial`
  - `/World/Looks/CubeMaterial`
  - `/World/Looks/SphereMaterial`
  - `/World/Geometry`
  - `/World/Geometry/Ground`
  - `/World/Actors`
  - `/World/Actors/LowBounceCube`
  - `/World/Actors/HighBounceSphere`
- World settings:
  - gravity: `(0, 0, -9.81)`
  - timestep: `60 Hz`
  - meters per unit: `1.0`
  - default prim: `/World`
  - solver token: `PhysxSchema.Tokens.TGS`
  - broadphase token: `PhysxSchema.Tokens.MBP`
  - enhanced determinism: enabled where supported by the installed Isaac Sim 6.0.1 bindings
- Material values:
  - ground: static friction `0.9`, dynamic friction `0.8`, restitution `0.0`
  - cube: static friction `0.85`, dynamic friction `0.75`, restitution `0.05`
  - sphere: static friction `0.05`, dynamic friction `0.03`, restitution `0.85`

## State-Source Policy

- Live PhysX runtime state is authoritative for acceptance decisions.
- Authored USD rigid-body velocities are retained only as `usd_sampled_*` diagnostics.
- Pose-derived velocity is a diagnostic cross-check.
- Sleep state is independently queried through PhysX.
- Angular speed is the magnitude of angular velocity in `rad/s`; it is not divided by timestep or frequency.

## Run Results

- Successful run count: `2`
- Completed steps: `433`
- Simulated duration: `7.216667 s`
- Step coverage: `866` CSV rows, `2` actors per step
- Inspection result: pass
- Comparison result: pass
- Comparison tolerances:
  - position: `0.001 m`
  - velocity: `0.001 m/s`
  - rebound height: `0.005 m`
  - step count: `1`
  - orientation: `0.000001`
  - angular velocity: `0.001 rad/s`
  - angular speed: `0.001 rad/s`
  - energy: `0.02 J`
  - simulation time: `0.000001 s`
- Maximum observed physics difference: `0.0` for every compared physics-bearing field

## Event Summary

- Cube first contact step: `0`
- Cube first sleep step: `23`
- Cube settle step: `41`
- Sphere first contact step: `32`
- Sphere first sleep step: `404`
- Sphere rebound step: `139`
- Sphere rebound height: `1.096437 m`
- Sphere settle step: `433`
- Shared run settle step: `433`
- Contact counts:
  - cube: `found 1`, `lost 0`, `persists 0`, `unknown 23`
  - sphere: `found 14`, `lost 13`, `persists 0`, `unknown 56`

## Final State

- Cube final position: `(-0.852279, 0.000027, 0.25)`
- Cube final orientation: `(0.000001, 0.000001, 0.000026, 1.0)`
- Cube final linear velocity: `(0.0, 0.0, 0.0)`
- Cube final angular velocity: `(0.0, 0.0, 0.0)`
- Sphere final position: `(1.0, 0.0, 0.250261)`
- Sphere final orientation: `(0.0, 0.0, 0.0, 1.0)`
- Sphere final linear velocity: `(0.0, 0.0, 0.0)`
- Sphere final angular velocity: `(0.0, 0.0, 0.0)`

## Energy Findings

- Cube initial total mechanical energy: `6.178678 J`
- Cube final total mechanical energy: `4.905001 J`
- Sphere initial total mechanical energy: `17.127401 J`
- Sphere final total mechanical energy: `2.455064 J`
- Final runtime kinetic energy for both actors: `0.0 J`
- Final runtime speed for both actors: `0.0 m/s`

## Canonical Hashes

- USDA: `d7254cbc33187e42a5137527c682518a4e39db7691b64d93d18ca3506df42e48`
- USD: `eccc945fc4dc26d3b688715adce7f096b1aff40b6f834e503bf473fd6731f599`
- run-01 trace CSV: `9de28520f274ff9f4ee062d74b787678bac3becccea5e4f678555c904483cf31`
- run-02 trace CSV: `6b4910fdfb1b16532ec73be23f0bc8ef4d2a3b42b1b9499e3a135159c646d36c`
- run-01 summary JSON: `59705588efefb6adb0be9dab01b51eb56615bb5d73a7b75057cf2aa6f448a14f`
- run-02 summary JSON: `3e5d5cf922edc5c14ecb9f400ec66d66600959d782cb256b772719ee18e1efe5`

## Validation Outcomes

- Scene authoring: complete
- Controlled simulation: complete
- Independent formal inspection: complete
- Cross-run reproducibility comparison: complete
- Canonical USDA files: byte-identical
- Canonical USD files: byte-identical
- Physics-bearing CSV and JSON values: semantically identical
- No unexplained differences remain
- Run-specific metadata explains the differing CSV and JSON hashes

## Warnings And Compatibility Notes

- `PhysxSchema.Tokens.TGS` and `PhysxSchema.Tokens.MBP` are the valid generated tokens in Isaac Sim 6.0.1; lowercase variants are unavailable.
- The formal authoring and formal inspection scripts use narrowly scoped one-shot containment after verified success because `SimulationApp.close()` reproduces the busy `TaskGroup` teardown defect in this environment.
- The simulation runner completed through the normal supported shutdown path and does not use `os._exit()`.
- Required contact-found and contact-lost outcomes were validated, but raw callback enum integers were not persisted, so the exact meaning of the normalized `contact_unknown` categories cannot be reconstructed from the completed artifacts alone.

## Artifact Boundaries

- Canonical generated `.usd` and `.usda` files remain ignored runtime outputs.
- `step_metrics.csv`, `summary.json`, `comparison.csv`, `comparison.json`, raw logs, caches, and Python bytecode remain ignored runtime outputs.
- The only intended tracked runtime-adjacent result artifact is this sanitized `results/summary.md`.
