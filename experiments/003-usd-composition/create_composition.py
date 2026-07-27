from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import sys

from isaacsim import SimulationApp


ROOT = Path(__file__).resolve().parent
ASSET_DIR = Path("/mnt/nvme/isaac/experiments/003-usd-composition/assets")
OUTPUT_DIR = Path("/mnt/nvme/isaac/experiments/003-usd-composition/output")
RESULTS_DIR = Path("/mnt/nvme/isaac/experiments/003-usd-composition/results")
HASH_MANIFEST = RESULTS_DIR / "source-asset-hashes.txt"
FRAMES = 10
Sdf = Usd = UsdGeom = UsdLux = Gf = None


LAB_ENV = OUTPUT_DIR / "lab_environment.usda"
BASE_ENV = OUTPUT_DIR / "base_environment.usda"
LIGHTING_LAYER = OUTPUT_DIR / "lighting_layer.usda"
ROOT_STAGE = OUTPUT_DIR / "composition_root.usda"
WRAPPER_STAGE = OUTPUT_DIR / "composition_wrapper.usda"


def fail(message: str) -> None:
    print(f"COMPOSITION: FAIL: {message}", flush=True)
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


def validate_hashes(paths):
    current = compute_hashes(paths)
    expected = load_manifest()
    if current != expected:
        fail("source assets changed since the manifest was written")


def layer_items(op_list):
    for attr in ("prependedItems", "explicitItems", "appendedItems"):
        items = getattr(op_list, attr, None)
        if items:
            return list(items)
    getter = getattr(op_list, "GetAddedOrExplicitItems", None)
    if getter is not None:
        return list(getter())
    return []


def validate_relative_asset_paths():
    lab_layer = Sdf.Layer.FindOrOpen(str(LAB_ENV))
    base_layer = Sdf.Layer.FindOrOpen(str(BASE_ENV))
    root_layer = Sdf.Layer.FindOrOpen(str(ROOT_STAGE))
    wrapper_layer = Sdf.Layer.FindOrOpen(str(WRAPPER_STAGE))
    for layer, label in (
        (lab_layer, "lab"),
        (base_layer, "base"),
        (root_layer, "root"),
        (wrapper_layer, "wrapper"),
    ):
        if layer is None:
            fail(f"failed to open {label} layer")

    def asset_paths(op_list):
        paths = []
        for item in layer_items(op_list):
            asset_path = getattr(item, "assetPath", "")
            if asset_path:
                paths.append(str(asset_path))
        return paths

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

    if not any(
        str(getattr(reference, "assetPath", "")) == "lab_environment.usda"
        for reference in layer_items(base_layer.GetPrimAtPath("/World").referenceList)
    ):
        fail("base environment reference path is not relative")

    root_sublayers = list(root_layer.subLayerPaths)
    if root_sublayers != ["lighting_layer.usda", "base_environment.usda"]:
        fail("composition_root subLayerPaths are not relative or not ordered correctly")

    if not any(
        str(getattr(reference, "assetPath", "")) == "composition_root.usda"
        for reference in layer_items(wrapper_layer.GetPrimAtPath("/World").referenceList)
    ):
        fail("wrapper reference path is not relative")


def open_stage(path: Path):
    stage = Usd.Stage.Open(str(path))
    if not stage:
        fail(f"failed to open stage: {path}")
    return stage


def set_default_prim(stage, prim_path: str):
    prim = stage.GetPrimAtPath(prim_path)
    if not prim or not prim.IsValid():
        fail(f"missing prim for default prim: {prim_path}")
    stage.SetDefaultPrim(prim)


def create_lab_environment():
    stage = Usd.Stage.CreateNew(str(LAB_ENV))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)

    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())

    ground = stage.OverridePrim("/World/Ground")
    ground.GetReferences().AddReference("../assets/ground.usda")
    UsdGeom.XformCommonAPI(ground).SetTranslate((0.0, 0.0, 0.0))

    lab = UsdGeom.Xform.Define(stage, "/World/Lab")
    UsdGeom.XformCommonAPI(lab).SetTranslate((0.0, 0.0, 0.0))

    cube = stage.OverridePrim("/World/Lab/RedCube")
    cube.GetReferences().AddReference("../assets/red_cube.usda")
    UsdGeom.XformCommonAPI(cube).SetTranslate((-1.0, 0.0, 0.25))

    sphere = stage.OverridePrim("/World/Lab/BlueSphere")
    sphere.GetReferences().AddReference("../assets/blue_sphere.usda")
    UsdGeom.XformCommonAPI(sphere).SetTranslate((1.0, 0.0, 0.25))

    marker = stage.OverridePrim("/World/Lab/YellowMarker")
    marker.GetReferences().AddReference("../assets/yellow_marker.usda")
    UsdGeom.XformCommonAPI(marker).SetTranslate((0.0, 0.9, 0.175))

    payload_area = stage.OverridePrim("/World/PayloadArea")
    payload_area.GetPayloads().AddPayload("../assets/payload_cluster.usda")
    UsdGeom.XformCommonAPI(payload_area).SetTranslate((2.5, 0.0, 0.0))

    stage.GetRootLayer().Save()


def create_base_environment():
    stage = Usd.Stage.CreateNew(str(BASE_ENV))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)

    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())
    world.GetPrim().GetReferences().AddReference("lab_environment.usda")

    light = UsdLux.DistantLight.Define(stage, "/World/Light")
    light.CreateIntensityAttr(1200.0)
    light.CreateColorAttr(Gf.Vec3f(0.95, 0.92, 0.85))

    stage.GetRootLayer().Save()


def create_lighting_layer():
    stage = Usd.Stage.CreateNew(str(LIGHTING_LAYER))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)

    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())

    light = UsdLux.DistantLight.Define(stage, "/World/Light")
    light.CreateIntensityAttr(3600.0)
    light.CreateColorAttr(Gf.Vec3f(1.0, 0.96, 0.88))
    light.CreateExposureAttr(0.35)

    stage.GetRootLayer().Save()


def create_root_stage():
    stage = Usd.Stage.CreateNew(str(ROOT_STAGE))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)

    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())
    stage.GetRootLayer().subLayerPaths = ["lighting_layer.usda", "base_environment.usda"]
    stage.GetRootLayer().Save()


def validate_root_composition(UsdGeom):
    stage = open_stage(ROOT_STAGE)
    root_layer = stage.GetRootLayer()
    if list(root_layer.subLayerPaths) != ["lighting_layer.usda", "base_environment.usda"]:
        fail("composition_root subLayerPaths order is incorrect")

    light = stage.GetPrimAtPath("/World/Light")
    if not light or not light.IsValid():
        fail("missing composed light prim")
    intensity = UsdLux.DistantLight(light).GetIntensityAttr().Get()
    if abs(float(intensity) - 3600.0) > 1e-9:
        fail(f"lighting layer did not win for intensity: {intensity}")

    base_stage = open_stage(BASE_ENV)
    base_light = base_stage.GetPrimAtPath("/World/Light")
    base_intensity = UsdLux.DistantLight(base_light).GetIntensityAttr().Get()
    if abs(float(base_intensity) - 1200.0) > 1e-9:
        fail(f"base environment light intensity mismatch: {base_intensity}")


def validate_payload_behavior():
    stage = Usd.Stage.Open(str(LAB_ENV), load=Usd.Stage.LoadNone)
    if not stage:
        fail(f"failed to open lab stage with LoadNone: {LAB_ENV}")

    payload = stage.GetPrimAtPath("/World/PayloadArea")
    if not payload or not payload.IsValid():
        fail("missing /World/PayloadArea with LoadNone")

    if payload.GetChildren():
        fail("payload children were visible before load")

    stage.Load(payload.GetPath())
    if not payload.GetChildren():
        fail("payload children did not appear after load")

    stage.Unload(payload.GetPath())
    if payload.GetChildren():
        fail("payload children remained visible after unload")


def create_wrapper_stage():
    stage = Usd.Stage.CreateNew(str(WRAPPER_STAGE))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)

    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())
    world.GetPrim().GetReferences().AddReference("composition_root.usda")
    world.GetPrim().CreateAttribute("phase5:compositionNote", Sdf.ValueTypeNames.String).Set(
        "wrapper stage adds stronger local opinions"
    )

    red_cube_prim = stage.OverridePrim("/World/Lab/RedCube")
    UsdGeom.XformCommonAPI(red_cube_prim).SetTranslate(Gf.Vec3d(-2.0, 0.4, 0.35))

    blue_sphere = UsdGeom.Gprim(stage.OverridePrim("/World/Lab/BlueSphere"))
    blue_sphere.CreateDisplayColorAttr([Gf.Vec3f(0.15, 0.8, 0.95)])

    marker = UsdGeom.Imageable(stage.OverridePrim("/World/Lab/YellowMarker"))
    marker.CreateVisibilityAttr().Set(UsdGeom.Tokens.invisible)

    light = UsdLux.DistantLight(stage.OverridePrim("/World/Light"))
    light.CreateIntensityAttr(4800.0)

    stage.GetRootLayer().Save()


def validate_wrapper_strength():
    stage = open_stage(WRAPPER_STAGE)

    red_cube = stage.GetPrimAtPath("/World/Lab/RedCube")
    translate = None
    xformable = UsdGeom.Xformable(red_cube)
    for op in xformable.GetOrderedXformOps():
        if op.GetOpType() == UsdGeom.XformOp.TypeTranslate:
            translate = tuple(op.Get())
            break
    if translate != (-2.0, 0.4, 0.35):
        fail(f"wrapper translate override failed: {translate}")

    blue_sphere = UsdGeom.Gprim(stage.GetPrimAtPath("/World/Lab/BlueSphere"))
    colors = blue_sphere.GetDisplayColorAttr().Get()
    if not colors or tuple(round(v, 6) for v in colors[0]) != (0.15, 0.8, 0.95):
        fail("wrapper color override failed")

    marker = stage.GetPrimAtPath("/World/Lab/YellowMarker")
    if marker.GetAttribute("visibility").Get() != "invisible":
        fail("wrapper marker visibility override failed")

    light = UsdLux.DistantLight(stage.GetPrimAtPath("/World/Light"))
    intensity = light.GetIntensityAttr().Get()
    if abs(float(intensity) - 4800.0) > 1e-9:
        fail("wrapper light override failed")


def validate_prim_stack_and_property_stack():
    stage = open_stage(WRAPPER_STAGE)
    red_cube = stage.GetPrimAtPath("/World/Lab/RedCube")
    prim_stack = red_cube.GetPrimStack()
    if len(prim_stack) < 2:
        fail("expected more than one prim stack opinion for /World/Lab/RedCube")

    translate_attr = red_cube.GetAttribute("xformOp:translate")
    if translate_attr is None:
        fail("expected xformOp:translate on /World/Lab/RedCube")
    property_stack = translate_attr.GetPropertyStack()
    if len(property_stack) < 2:
        fail("expected more than one property stack opinion for xformOp:translate")


def validate_source_assets_unchanged():
    source_assets = [
        ROOT / "assets" / "red_cube.usda",
        ROOT / "assets" / "blue_sphere.usda",
        ROOT / "assets" / "yellow_marker.usda",
        ROOT / "assets" / "ground.usda",
        ROOT / "assets" / "payload_cluster.usda",
    ]
    validate_hashes(source_assets)


def validate_relative_paths():
    root_stage = open_stage(ROOT_STAGE)
    open_stage(WRAPPER_STAGE)

    if list(root_stage.GetRootLayer().subLayerPaths) != ["lighting_layer.usda", "base_environment.usda"]:
        fail("expected relative sublayer paths for composition_root")

    expected_text = {
        LAB_ENV: [
            "prepend references = @../assets/ground.usda@",
            "prepend references = @../assets/red_cube.usda@",
            "prepend references = @../assets/blue_sphere.usda@",
            "prepend references = @../assets/yellow_marker.usda@",
            "prepend payload = @../assets/payload_cluster.usda@",
        ],
        BASE_ENV: ["prepend references = @lab_environment.usda@"],
        ROOT_STAGE: ["@lighting_layer.usda@", "@base_environment.usda@"],
        WRAPPER_STAGE: ["prepend references = @composition_root.usda@"],
    }
    for path, snippets in expected_text.items():
        text = path.read_text(encoding="utf-8")
        if "://" in text:
            fail(f"unexpected external URL in {path.name}")
        for snippet in snippets:
            if snippet not in text:
                fail(f"missing relative authored path in {path.name}: {snippet}")


def validate_default_prims():
    expected = {
        ROOT / "assets" / "red_cube.usda": "RedCube",
        ROOT / "assets" / "blue_sphere.usda": "BlueSphere",
        ROOT / "assets" / "yellow_marker.usda": "YellowMarker",
        ROOT / "assets" / "ground.usda": "Ground",
        ROOT / "assets" / "payload_cluster.usda": "PayloadCluster",
        LAB_ENV: "World",
        BASE_ENV: "World",
        LIGHTING_LAYER: "World",
        ROOT_STAGE: "World",
        WRAPPER_STAGE: "World",
    }
    for path, default_name in expected.items():
        stage = open_stage(path)
        default_prim = stage.GetDefaultPrim()
        if not default_prim or default_prim.GetName() != default_name:
            fail(f"{path} default prim mismatch: {default_prim.GetName() if default_prim else None}")


def run_frames(app):
    for _ in range(FRAMES):
        app.update()


def main() -> int:
    app = SimulationApp({"headless": True})
    exit_code = 0

    try:
        global Sdf, Usd, UsdGeom, UsdLux, Gf
        from pxr import Gf as _Gf, Sdf as _Sdf, Usd as _Usd, UsdGeom as _UsdGeom, UsdLux as _UsdLux

        Sdf = _Sdf
        Usd = _Usd
        UsdGeom = _UsdGeom
        UsdLux = _UsdLux
        Gf = _Gf

        validate_source_assets_unchanged()
        create_lab_environment()
        print("COMPOSITION: reference stage created", flush=True)
        print("COMPOSITION: payload authored", flush=True)
        validate_payload_behavior()
        print("COMPOSITION: payload unloaded validation passed", flush=True)
        print("COMPOSITION: payload loaded validation passed", flush=True)

        create_base_environment()
        create_lighting_layer()
        create_root_stage()
        print("COMPOSITION: sublayer stack created", flush=True)
        create_wrapper_stage()
        print("COMPOSITION: wrapper overrides authored", flush=True)

        validate_relative_paths()
        validate_root_composition(UsdGeom)
        validate_wrapper_strength()
        validate_prim_stack_and_property_stack()

        validate_source_assets_unchanged()
        print("COMPOSITION: source assets unchanged", flush=True)

        run_frames(app)
        print("COMPOSITION: 10 frames completed", flush=True)
        print("COMPOSITION: composed values validated", flush=True)
    except Exception:
        exit_code = 1
        import traceback

        traceback.print_exc()
    finally:
        print("COMPOSITION: requesting immediate shutdown", flush=True)
        app.close(skip_cleanup=True, exit_code=exit_code)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
