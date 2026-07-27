# USD Composition Foundations

Phase 5 is the OpenUSD composition lab for the Physical AI Lab.

This experiment is designed to teach the composition tools that matter when a
scene moves from a hand-authored toy example toward a real-world environment
capture:

- references
- payloads
- sublayers
- overrides
- default prims
- layer strength
- wrapper stages
- prim stacks
- property stacks
- relative asset paths
- non-destructive customization

The core rule is simple: source layers stay immutable. Composition should add
stronger opinions around reusable layers, not rewrite the reusable layers
themselves.

Phase 5 is complete. This experiment now serves as the reference composition
model for future wrapper stages around real-world environments, OVER USDZ
captures, robot assets, sensors, and simulation configuration.

## What This Lab Demonstrates

### References

The `lab_environment.usda` stage references reusable asset layers for the
ground, cube, sphere, and marker. Each asset has its own meaningful default
prim, and the referencing prim controls placement through transforms.

References are used when the scene needs a reusable asset to appear at a
specific namespace path.

### Payloads

The `lab_environment.usda` stage also authors a payload at `/World/PayloadArea`.
The payload prim exists in the namespace even when unloaded, but its child
contents only appear after the payload is loaded.

Payloads are the right tool when a scene should keep structure visible while
deferring heavy content until it is needed.

### Sublayers

`composition_root.usda` assembles `lighting_layer.usda` and
`base_environment.usda` through sublayers.

The required strength order is:

1. `lighting_layer.usda` first, therefore strongest
2. `base_environment.usda` second, therefore weaker

This lab validates both the authored `subLayerPaths` order and a composed
opinion that proves the stronger lighting layer wins.

### Overrides

`composition_wrapper.usda` is the wrapper stage. It references the composed
root stage and authors local non-destructive overrides on top.

The wrapper stage demonstrates that:

- local opinions override referenced opinions
- the reusable source layers remain unchanged
- a prim stack can include opinions from more than one layer
- a property stack can show the stronger authored opinion winning

### Default Prims and Layer Stacks

Every reusable asset has a default prim so it can be referenced cleanly.

The composed stages also validate layer stack ordering and default prim
selection so the design is ready for future environment captures that may be
authored as a wrapper around a captured scene.

## File Layout

Tracked source files:

- `assets/red_cube.usda`
- `assets/blue_sphere.usda`
- `assets/yellow_marker.usda`
- `assets/ground.usda`
- `assets/payload_cluster.usda`
- `create_assets.py`
- `create_composition.py`
- `inspect_composition.py`
- `expected-results.md`
- `expected-hierarchy.txt`
- `expected-layer-stack.txt`

Generated runtime files live under:

- `/mnt/nvme/isaac/experiments/003-usd-composition/assets`
- `/mnt/nvme/isaac/experiments/003-usd-composition/output`
- `/mnt/nvme/isaac/experiments/003-usd-composition/results`

## Composition Graph

The wrapper stage follows this graph:

```text
composition_wrapper.usda
  -> local /World prim
  -> reference to the default prim of composition_root.usda
  -> local wrapper overrides authored in composition_wrapper.usda
```

The root stage follows this graph:

```text
composition_root.usda
  -> sublayers: lighting_layer.usda, then base_environment.usda
  -> base_environment.usda references lab_environment.usda
  -> lab_environment.usda references reusable assets and authors a payload
```

That wrapper-stage pattern is what will let a future experiment substitute a
captured environment such as `capture.usdz` for `lab_environment.usda` without
redesigning the composition workflow.

## Running The Lab

Prepare the runtime directories:

```bash
make prepare-usd-composition
```

Prepare ownership only when explicitly approved:

```bash
sudo make prepare-usd-composition-ownership CONFIRM_CHOWN=1
```

Validate ownership from a short-lived container:

```bash
make validate-usd-composition-ownership
```

Generate assets:

```bash
make run-usd-composition-assets
```

Generate the composed stages:

```bash
make run-usd-composition
```

Run the independent inspector:

```bash
make inspect-usd-composition
```

The independent inspector is intentionally one-shot. It performs read-only
validation, prints its success markers, and exits directly with `os._exit()`
because Isaac Sim 6.0.1 teardown was observed to fail after successful
validation when using the normal close paths.

Run the static refinement checks:

```bash
make test-phase5
```

## Future OVER/USDZ Compatibility

This lab intentionally uses a wrapper-stage pattern so a future experiment can
replace `lab_environment.usda` with a future capture such as `capture.usdz`
without redesigning the composition workflow.

That future step is intentionally not implemented yet. This phase only prepares
the composition model and the validation contract.

## Known Teardown Issue

The disposable read-only inspector is the only place where the one-shot
`os._exit()` workaround is used.

- `SimulationApp.close(skip_cleanup=True)` failed with a busy TaskGroup abort
- a graceful teardown path failed with a post-validation segmentation fault
- the inspector now validates all state first, then flushes output and exits
  directly so a successful immutable read-only validation is not marked failed
  because of the known Isaac Sim 6.0.1 native teardown defect
- authoring scripts and any long-lived Isaac Sim services must continue to use
  their validated shutdown behavior
