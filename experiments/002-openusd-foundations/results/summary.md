# Phase 4 Summary

Date: 2026-07-27

## Isaac Sim

- Image: `nvcr.io/nvidia/isaac-sim:6.0.1`
- Digest: `sha256:783444c706538aa76cf5126e911ddc5e618779e6105305ad4af4260362a30aa9`

## Scene

The generated stage contains:

- `/World` (`Xform`)
- `/World/Ground` (`Mesh`)
- `/World/Light` (`DistantLight`)
- `/World/Lab` (`Xform`)
- `/World/Lab/RedCube` (`Cube`)
- `/World/Lab/BlueSphere` (`Sphere`)
- `/World/Lab/Marker` (`Cylinder`)
- `/World/Camera` (`Camera`)

## Stage Metadata

- Default prim: `/World`
- Up-axis: `Z`
- Meters-per-unit: `1.0`

## Generated Files

- `output/openusd_foundations.usda`
  - Format: `usda`
  - Size: `1760 bytes`
- `output/openusd_foundations.usd`
  - Format: `usd` / binary USDC
  - Size: `2050 bytes`

## Results

- Creation result: passed
- Inspection result: passed
- Frame count: `10`
- Shutdown method: `SimulationApp.close(skip_cleanup=True, exit_code=exit_code)`
- Final exit code: `0`

## Known Nonfatal Warnings

- OmniHub reconnect warnings
- no default display
- GLFW initialization warning
- IOMMU enabled
- muted USD diagnostics
- `pxr.Semantics` deprecation warning

## Phase Status

- Phase 4A complete
- Phase 4B complete
- Phase 4 overall complete
- Next milestone: Phase 4C / Phase 5, covering USD layers, references, and composition for future real-world environment ingestion such as OVER USDZ captures

