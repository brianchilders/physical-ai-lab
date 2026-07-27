from __future__ import annotations

import os
from hashlib import sha256
from pathlib import Path
import sys
import traceback

from isaacsim import SimulationApp


ROOT = Path(__file__).resolve().parent
ASSET_FILES = [
    ROOT / "assets" / "red_cube.usda",
    ROOT / "assets" / "blue_sphere.usda",
    ROOT / "assets" / "yellow_marker.usda",
    ROOT / "assets" / "ground.usda",
    ROOT / "assets" / "payload_cluster.usda",
]
OUTPUT_DIR = Path("/mnt/nvme/isaac/experiments/003-usd-composition/output")
HASH_MANIFEST = Path("/mnt/nvme/isaac/experiments/003-usd-composition/results/source-asset-hashes.txt")
Sdf = Usd = UsdGeom = UsdLux = None


ROOT_STAGE = OUTPUT_DIR / "composition_root.usda"
WRAPPER_STAGE = OUTPUT_DIR / "composition_wrapper.usda"
LAB_ENV = OUTPUT_DIR / "lab_environment.usda"
BASE_ENV = OUTPUT_DIR / "base_environment.usda"
LIGHTING_LAYER = OUTPUT_DIR / "lighting_layer.usda"


def fail(message: str) -> None:
    print(f"COMPOSITION_INSPECT: FAIL: {message}", flush=True)
    raise RuntimeError(message)


def compute_hashes(paths):
    hashes = {}
    for path in paths:
        hashes[path.name] = sha256(path.read_bytes()).hexdigest()
    return hashes


def load_manifest():
    if not HASH_MANIFEST.is_file():
        fail(f"missing hash manifest: {HASH_MANIFEST}")
    hashes = {}
    with HASH_MANIFEST.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            name, digest = line.split(maxsplit=1)
            hashes[name] = digest
    return hashes


def layer_items(op_list):
    for attr in ("prependedItems", "explicitItems", "appendedItems"):
        items = getattr(op_list, attr, None)
        if items:
            return list(items)
    getter = getattr(op_list, "GetAddedOrExplicitItems", None)
    if getter is not None:
        return list(getter())
    return []


def validate_source_hashes():
    current = compute_hashes(ASSET_FILES)
    expected = load_manifest()
    if current != expected:
        fail("source layers changed unexpectedly")


def open_stage(path: Path):
    stage = Usd.Stage.Open(str(path))
    if not stage:
        fail(f"failed to open stage: {path}")
    return stage


def print_tree(prim, indent=0):
    if not prim or not prim.IsValid():
        return
    prefix = "  " * indent
    print(f"{prefix}{prim.GetPath()} ({prim.GetTypeName()})", flush=True)
    for child in prim.GetChildren():
        print_tree(child, indent + 1)


def validate_default_prims():
    for path in [LAB_ENV, BASE_ENV, LIGHTING_LAYER, ROOT_STAGE, WRAPPER_STAGE]:
        stage = open_stage(path)
        default_prim = stage.GetDefaultPrim()
        if not default_prim or default_prim.GetPath().pathString != "/World":
            fail(f"{path} does not have /World as the default prim")

    for asset_path, expected_name in (
        (ROOT / "assets" / "red_cube.usda", "RedCube"),
        (ROOT / "assets" / "blue_sphere.usda", "BlueSphere"),
        (ROOT / "assets" / "yellow_marker.usda", "YellowMarker"),
        (ROOT / "assets" / "ground.usda", "Ground"),
        (ROOT / "assets" / "payload_cluster.usda", "PayloadCluster"),
    ):
        stage = open_stage(asset_path)
        if stage.GetDefaultPrim().GetName() != expected_name:
            fail(f"{asset_path} default prim mismatch")


def validate_root_layer_order(stage):
    sublayers = list(stage.GetRootLayer().subLayerPaths)
    if sublayers != ["lighting_layer.usda", "base_environment.usda"]:
        fail(f"unexpected subLayerPaths order: {sublayers}")

    print(f"COMPOSITION_INSPECT: root sublayers={sublayers}", flush=True)


def validate_references(stage):
    prim = stage.GetPrimAtPath("/World")
    if not prim or not prim.IsValid():
        fail("missing /World prim in wrapper stage")

    wrapper_layer = Sdf.Layer.FindOrOpen(str(WRAPPER_STAGE))
    if wrapper_layer is None:
        fail("failed to open wrapper layer for reference inspection")
    wrapper_world = wrapper_layer.GetPrimAtPath("/World")
    references = layer_items(wrapper_world.referenceList)
    if not references:
        fail("wrapper stage is missing reference metadata")
    if not any(str(getattr(reference, "assetPath", "")) == "composition_root.usda" for reference in references):
        fail("wrapper reference path is not relative")
    print(
        "COMPOSITION_INSPECT: wrapper references="
        f"{[str(getattr(reference, 'assetPath', '')) for reference in references]}",
        flush=True,
    )

    lab = stage.GetPrimAtPath("/World/Lab/RedCube")
    if not lab or not lab.IsValid():
        fail("missing wrapped red cube")

    stack = lab.GetPrimStack()
    if len(stack) < 2:
        fail("expected multiple prim stack entries for wrapped red cube")


def validate_payload_states():
    stage = Usd.Stage.Open(str(LAB_ENV), load=Usd.Stage.LoadNone)
    if not stage:
        fail("failed to open lab environment with LoadNone")

    payload = stage.GetPrimAtPath("/World/PayloadArea")
    if not payload or not payload.IsValid():
        fail("missing /World/PayloadArea")
    if payload.GetChildren():
        fail("payload children should not be visible before load")

    stage.Load(payload.GetPath())
    if not payload.GetChildren():
        fail("payload children did not appear after load")

    stage.Unload(payload.GetPath())
    if payload.GetChildren():
        fail("payload children remained visible after unload")
    print("COMPOSITION_INSPECT: payload load state toggled LoadNone -> Load -> Unload", flush=True)


def validate_sublayer_opinion():
    stage = open_stage(ROOT_STAGE)
    light = UsdLux.DistantLight(stage.GetPrimAtPath("/World/Light"))
    intensity = light.GetIntensityAttr().Get()
    if abs(float(intensity) - 3600.0) > 1e-9:
        fail(f"lighting layer did not win over base environment: {intensity}")


def validate_property_stack():
    stage = open_stage(WRAPPER_STAGE)
    red_cube = stage.GetPrimAtPath("/World/Lab/RedCube")
    translate_attr = red_cube.GetAttribute("xformOp:translate")
    if len(translate_attr.GetPropertyStack()) < 2:
        fail("expected translate property stack to contain multiple opinions")
    if tuple(translate_attr.Get()) != (-2.0, 0.4, 0.35):
        fail("wrapper translate opinion did not win")
    print(
        f"COMPOSITION_INSPECT: translate property stack depth={len(translate_attr.GetPropertyStack())}",
        flush=True,
    )


def validate_overrides():
    stage = open_stage(WRAPPER_STAGE)
    blue = UsdGeom.Gprim(stage.GetPrimAtPath("/World/Lab/BlueSphere"))
    colors = blue.GetDisplayColorAttr().Get()
    if not colors or tuple(round(v, 6) for v in colors[0]) != (0.15, 0.8, 0.95):
        fail("blue sphere override was not composed")
    marker = stage.GetPrimAtPath("/World/Lab/YellowMarker")
    if marker.GetAttribute("visibility").Get() != "invisible":
        fail("yellow marker visibility override was not composed")


def validate_relative_paths():
    root_stage = open_stage(ROOT_STAGE)
    wrapper_stage = open_stage(WRAPPER_STAGE)

    if list(root_stage.GetRootLayer().subLayerPaths) != ["lighting_layer.usda", "base_environment.usda"]:
        fail("root sublayer order is incorrect")

    lab_layer = Sdf.Layer.FindOrOpen(str(LAB_ENV))
    base_layer = Sdf.Layer.FindOrOpen(str(BASE_ENV))
    wrapper_layer = Sdf.Layer.FindOrOpen(str(WRAPPER_STAGE))
    if lab_layer is None or base_layer is None or wrapper_layer is None:
        fail("failed to reopen layer specs for relative path validation")

    def asset_paths(op_list):
        return [str(getattr(item, "assetPath", "")) for item in layer_items(op_list) if getattr(item, "assetPath", "")]

    if "../assets/ground.usda" not in asset_paths(lab_layer.GetPrimAtPath("/World/Ground").referenceList):
        fail("ground reference path is not relative")
    if "../assets/red_cube.usda" not in asset_paths(lab_layer.GetPrimAtPath("/World/Lab/RedCube").referenceList):
        fail("red cube reference path is not relative")
    if "../assets/blue_sphere.usda" not in asset_paths(lab_layer.GetPrimAtPath("/World/Lab/BlueSphere").referenceList):
        fail("blue sphere reference path is not relative")
    if "../assets/yellow_marker.usda" not in asset_paths(lab_layer.GetPrimAtPath("/World/Lab/YellowMarker").referenceList):
        fail("yellow marker reference path is not relative")
    if "../assets/payload_cluster.usda" not in asset_paths(lab_layer.GetPrimAtPath("/World/PayloadArea").payloadList):
        fail("payload path is not relative")
    if "lab_environment.usda" not in asset_paths(base_layer.GetPrimAtPath("/World").referenceList):
        fail("base environment reference path is not relative")
    if "composition_root.usda" not in asset_paths(wrapper_layer.GetPrimAtPath("/World").referenceList):
        fail("wrapper reference path is not relative")


def validate_generated_files():
    required = [
        ROOT / "assets" / "red_cube.usda",
        ROOT / "assets" / "blue_sphere.usda",
        ROOT / "assets" / "yellow_marker.usda",
        ROOT / "assets" / "ground.usda",
        ROOT / "assets" / "payload_cluster.usda",
        LAB_ENV,
        BASE_ENV,
        LIGHTING_LAYER,
        ROOT_STAGE,
        WRAPPER_STAGE,
    ]
    for path in required:
        if not path.is_file():
            fail(f"missing generated file: {path}")
        if not Usd.Stage.Open(str(path)):
            fail(f"failed to open generated file: {path}")


def validate_prim_stack():
    stage = open_stage(WRAPPER_STAGE)
    prim = stage.GetPrimAtPath("/World/Lab/RedCube")
    if len(prim.GetPrimStack()) < 2:
        fail("prim stack validation failed for /World/Lab/RedCube")
    print(f"COMPOSITION_INSPECT: red cube prim stack depth={len(prim.GetPrimStack())}", flush=True)


def print_hierarchy(stage, label):
    print(f"COMPOSITION_INSPECT: {label} hierarchy", flush=True)
    print_tree(stage.GetPseudoRoot(), 0)


def flush_streams() -> None:
    sys.stdout.flush()
    sys.stderr.flush()


def run_validation() -> None:
    try:
        global Sdf, Usd, UsdGeom, UsdLux
        from pxr import Sdf as _Sdf, Usd as _Usd, UsdGeom as _UsdGeom, UsdLux as _UsdLux

        Sdf = _Sdf
        Usd = _Usd
        UsdGeom = _UsdGeom
        UsdLux = _UsdLux

        validate_source_hashes()
        print("COMPOSITION_INSPECT: root stage opened", flush=True)
        root_stage = open_stage(ROOT_STAGE)
        print("COMPOSITION_INSPECT: wrapper stage opened", flush=True)
        wrapper_stage = open_stage(WRAPPER_STAGE)

        print(f"COMPOSITION_INSPECT: root layer={root_stage.GetRootLayer().identifier}", flush=True)
        print(f"COMPOSITION_INSPECT: wrapper layer={wrapper_stage.GetRootLayer().identifier}", flush=True)
        print_hierarchy(root_stage, "root")
        print_hierarchy(wrapper_stage, "wrapper")

        validate_generated_files()
        validate_default_prims()
        validate_relative_paths()
        validate_references(wrapper_stage)
        print("COMPOSITION_INSPECT: references validated", flush=True)

        validate_payload_states()
        print("COMPOSITION_INSPECT: payload states validated", flush=True)

        validate_root_layer_order(root_stage)
        validate_sublayer_opinion()
        print("COMPOSITION_INSPECT: sublayer order validated", flush=True)

        validate_prim_stack()
        validate_property_stack()
        print("COMPOSITION_INSPECT: prim stack validated", flush=True)

        validate_overrides()
        print("COMPOSITION_INSPECT: overrides validated", flush=True)

        validate_source_hashes()
        print("COMPOSITION_INSPECT: source layers unchanged", flush=True)
        print("COMPOSITION_INSPECT: inspection passed", flush=True)
    except Exception:
        traceback.print_exc()
        flush_streams()
        os._exit(1)

    print("COMPOSITION_INSPECT: terminating one-shot inspector", flush=True)
    flush_streams()
    os._exit(0)


def main() -> int:
    # This disposable inspector runs inside a one-shot container. Both Isaac Sim 6.0.1
    # shutdown paths were exercised and failed after validation completed, so we do not
    # call the standard close path here. Direct process termination preserves the success
    # or failure signal for this immutable read-only validator. Long-lived services and
    # authoring scripts must continue to use the validated shutdown paths.
    app = SimulationApp({"headless": True})
    _ = app
    run_validation()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
