# Expected Results

Phase 5 should demonstrate OpenUSD composition foundations in a way that is
small enough to inspect by hand and strong enough to support future captured
environments.

## Expected Artifacts

Reusable source assets:

- `assets/red_cube.usda`
- `assets/blue_sphere.usda`
- `assets/yellow_marker.usda`
- `assets/ground.usda`
- `assets/payload_cluster.usda`

Composed runtime stages:

- `output/lab_environment.usda`
- `output/base_environment.usda`
- `output/lighting_layer.usda`
- `output/composition_root.usda`
- `output/composition_wrapper.usda`

## Expected Composition Behavior

- references place reusable assets at fixed namespace paths
- payloads remain visible in the namespace while their children are unloaded
- payload contents appear after load and disappear after unload
- sublayer ordering makes `lighting_layer.usda` stronger than
  `base_environment.usda`
- wrapper opinions are stronger than referenced opinions
- source layers remain unchanged after composition and inspection
- all authored asset paths, reference paths, payload paths, and sublayer paths
  are relative

## Expected Console Markers

Asset generation:

- `COMPOSITION: SimulationApp initialized`
- `COMPOSITION: reusable assets created`
- `COMPOSITION: asset default prims validated`
- `COMPOSITION: requesting immediate shutdown`

Composition generation:

- `COMPOSITION: reference stage created`
- `COMPOSITION: payload authored`
- `COMPOSITION: payload unloaded validation passed`
- `COMPOSITION: payload loaded validation passed`
- `COMPOSITION: sublayer stack created`
- `COMPOSITION: wrapper overrides authored`
- `COMPOSITION: source assets unchanged`
- `COMPOSITION: composed values validated`
- `COMPOSITION: 10 frames completed`
- `COMPOSITION: requesting immediate shutdown`

Inspection:

- `COMPOSITION_INSPECT: root stage opened`
- `COMPOSITION_INSPECT: wrapper stage opened`
- `COMPOSITION_INSPECT: references validated`
- `COMPOSITION_INSPECT: payload states validated`
- `COMPOSITION_INSPECT: sublayer order validated`
- `COMPOSITION_INSPECT: prim stack validated`
- `COMPOSITION_INSPECT: overrides validated`
- `COMPOSITION_INSPECT: source layers unchanged`
- `COMPOSITION_INSPECT: inspection passed`
- `COMPOSITION_INSPECT: terminating one-shot inspector`

## Failure Conditions

- any non-relative authored path
- any source asset hash mismatch
- any missing default prim
- any missing or reversed sublayer ordering
- any payload child visible while unloaded
- any wrapper override failing to outrank the referenced opinion
- any failure to flush and terminate the disposable inspector after validation
