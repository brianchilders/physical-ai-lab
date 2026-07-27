# OpenUSD Foundations

This lab is the first reproducible OpenUSD exercise in the Physical AI Lab.

It focuses on the scenegraph fundamentals that show up in almost every USD workflow:

- stages
- prims
- namespaces and paths
- Xform hierarchy
- geometry schemas
- transforms
- attributes
- root layers
- saving and reopening a stage
- text-based USDA inspection
- stage validation

Phase 4A authoring and Phase 4B inspection are complete. The next milestone is
Phase 4C / Phase 5: USD layers, references, and composition.

## Concepts

### What Is a Stage

A USD stage is the composed scenegraph presented by the USD runtime. It is the thing you open, traverse, inspect, and validate.

### What Is a Prim

A prim is a persistent scenegraph object on the stage. In practice, prims are the named nodes you define at paths like `/World/Lab/RedCube`.

### Why `/World`

`/World` is used as the default prim because it is a clear, common top-level namespace for the visible scene content. It keeps the lab organized and makes the saved files easy to read.

### Why Xform Prims Matter

`UsdGeom.Xform` prims organize hierarchy without forcing geometry. They are the natural way to group scene content such as a lab area or a robot cell.

### `.usda` Versus `.usd`

- `.usda` is human-readable text and is ideal for inspection and diffing.
- `.usd` is the binary USDC container in this lab and is useful for compact, reproducible stage storage.

This lab writes both so you can inspect the scene as text and also verify the binary export path.

### Default Prim

The default prim is the main root prim a stage should present to consumers. This lab sets it to `/World`.

### Up-Axis and Meters-Per-Unit

The stage explicitly authors:

- up-axis
- meters-per-unit

That makes transforms and scale unambiguous when the files are reopened elsewhere.

## Files

- `create_scene.py` builds the stage, saves both file formats, reopens them, validates the content, and runs 10 frames.
- `inspect_scene.py` opens the saved USDA file and prints the hierarchy and key metadata.
- `expected-hierarchy.txt` documents the intended scene tree.

## How To Run

The writable experiment artifacts live under the isolated NVMe tree at
`/mnt/nvme/isaac/experiments/002-openusd-foundations/` and are mounted into the
container at `output/` and `results/`.

Prepare the directories first:

```bash
make prepare-openusd-lab
```

Prepare ownership only when needed:

```bash
sudo make prepare-openusd-lab-ownership CONFIRM_CHOWN=1
```

Validate the static repository checks:

```bash
make validate-openusd-lab
```

Run the scene builder:

```bash
make run-openusd-lab
```

Inspect the saved USDA:

```bash
make inspect-openusd-lab
```

## Expected Output

The scene builder prints deterministic `OPENUSD:` milestones, saves both `output/openusd_foundations.usda` and `output/openusd_foundations.usd`, validates the reopened stages, and shuts down cleanly.

The inspector prints the hierarchy, prim paths, prim types, default prim, stage up-axis, meters-per-unit, and layer formats for both saved files.

## Cleanup

Generated `.usd`, `.usda`, and `.log` files remain ignored by git. Remove them manually if you want a fresh run; the repository does not prune them automatically.
