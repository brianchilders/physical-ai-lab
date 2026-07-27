from __future__ import annotations

from pathlib import Path
import sys
import traceback

from isaacsim import SimulationApp


APP_CONFIG = {"headless": True}
FRAMES = 10
ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output"
USDA_PATH = OUTPUT_DIR / "openusd_foundations.usda"
USD_PATH = OUTPUT_DIR / "openusd_foundations.usd"


def fail(message: str) -> None:
    print(f"OPENUSD: FAIL: {message}", flush=True)
    raise RuntimeError(message)


def validate_layer_file(path: Path, expected_prefix: bytes, label: str) -> None:
    if not path.is_file():
        fail(f"{label} missing: {path}")
    with path.open("rb") as fh:
        header = fh.read(len(expected_prefix))
    if header != expected_prefix:
        fail(f"{label} has unexpected file signature: {header!r}")


def layer_format_info(layer):
    file_format = layer.GetFileFormat()
    format_id = getattr(file_format, "formatId", None)
    if format_id is None and hasattr(file_format, "GetFormatId"):
        format_id = file_format.GetFormatId()
    file_extension = getattr(layer, "fileExtension", None)
    if file_extension is None and hasattr(layer, "GetFileExtension"):
        file_extension = layer.GetFileExtension()
    file_format_arguments = getattr(layer, "fileFormatArguments", None)
    if file_format_arguments is None and hasattr(layer, "GetFileFormatArguments"):
        file_format_arguments = layer.GetFileFormatArguments()
    return format_id, file_extension, dict(file_format_arguments or {})


def author_scene(Usd, UsdGeom, UsdLux, Gf):
    stage = Usd.Stage.CreateNew(str(USDA_PATH))
    print("OPENUSD: stage created", flush=True)

    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)

    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())
    print("OPENUSD: default prim set to /World", flush=True)

    ground = UsdGeom.Mesh.Define(stage, "/World/Ground")
    ground.CreatePointsAttr(
        [
            Gf.Vec3f(-5.0, -5.0, 0.0),
            Gf.Vec3f(5.0, -5.0, 0.0),
            Gf.Vec3f(5.0, 5.0, 0.0),
            Gf.Vec3f(-5.0, 5.0, 0.0),
        ]
    )
    ground.CreateFaceVertexCountsAttr([3, 3])
    ground.CreateFaceVertexIndicesAttr([0, 1, 2, 0, 2, 3])
    ground.CreateDoubleSidedAttr(True)
    ground.CreateDisplayColorAttr([Gf.Vec3f(0.2, 0.2, 0.2)])

    light = UsdLux.DistantLight.Define(stage, "/World/Light")
    light.CreateIntensityAttr(3000.0)
    light_xform = UsdGeom.XformCommonAPI(light)
    light_xform.SetRotate(Gf.Vec3f(-55.0, 0.0, 35.0))

    lab = UsdGeom.Xform.Define(stage, "/World/Lab")
    lab_xform = UsdGeom.XformCommonAPI(lab)
    lab_xform.SetTranslate(Gf.Vec3d(0.0, 0.0, 0.0))

    cube = UsdGeom.Cube.Define(stage, "/World/Lab/RedCube")
    cube.CreateSizeAttr(0.5)
    cube.CreateDisplayColorAttr([Gf.Vec3f(1.0, 0.0, 0.0)])
    UsdGeom.XformCommonAPI(cube).SetTranslate(Gf.Vec3d(-1.0, 0.0, 0.25))

    sphere = UsdGeom.Sphere.Define(stage, "/World/Lab/BlueSphere")
    sphere.CreateRadiusAttr(0.25)
    sphere.CreateDisplayColorAttr([Gf.Vec3f(0.0, 0.0, 1.0)])
    UsdGeom.XformCommonAPI(sphere).SetTranslate(Gf.Vec3d(1.0, 0.0, 0.25))

    marker = UsdGeom.Cylinder.Define(stage, "/World/Lab/Marker")
    marker.CreateRadiusAttr(0.12)
    marker.CreateHeightAttr(0.35)
    marker.CreateDisplayColorAttr([Gf.Vec3f(1.0, 1.0, 0.0)])
    UsdGeom.XformCommonAPI(marker).SetTranslate(Gf.Vec3d(0.0, 0.9, 0.175))

    camera = UsdGeom.Camera.Define(stage, "/World/Camera")
    camera_xform = UsdGeom.XformCommonAPI(camera)
    camera_xform.SetTranslate(Gf.Vec3d(0.0, -5.0, 2.5))
    camera_xform.SetRotate(Gf.Vec3f(-65.0, 0.0, 0.0))

    print("OPENUSD: geometry created", flush=True)
    print("OPENUSD: transforms applied", flush=True)
    return stage


def prim_translate(UsdGeom, prim):
    xform = UsdGeom.Xformable(prim)
    for op in xform.GetOrderedXformOps():
        if op.GetOpType() == UsdGeom.XformOp.TypeTranslate:
            return tuple(op.Get())
    return None


def validate_stage(stage, UsdGeom):
    expected = {
        "/World": "Xform",
        "/World/Ground": "Mesh",
        "/World/Light": "DistantLight",
        "/World/Lab": "Xform",
        "/World/Lab/RedCube": "Cube",
        "/World/Lab/BlueSphere": "Sphere",
        "/World/Lab/Marker": "Cylinder",
        "/World/Camera": "Camera",
    }
    expected_translates = {
        "/World/Lab": (0.0, 0.0, 0.0),
        "/World/Lab/RedCube": (-1.0, 0.0, 0.25),
        "/World/Lab/BlueSphere": (1.0, 0.0, 0.25),
        "/World/Lab/Marker": (0.0, 0.9, 0.175),
        "/World/Camera": (0.0, -5.0, 2.5),
    }
    expected_colors = {
        "/World/Lab/RedCube": (1.0, 0.0, 0.0),
        "/World/Lab/BlueSphere": (0.0, 0.0, 1.0),
        "/World/Lab/Marker": (1.0, 1.0, 0.0),
    }

    default_prim = stage.GetDefaultPrim()
    if not default_prim or default_prim.GetPath().pathString != "/World":
        fail("default prim is not /World")

    if UsdGeom.GetStageUpAxis(stage) != UsdGeom.Tokens.z:
        fail("stage up-axis is not z")

    meters_per_unit = UsdGeom.GetStageMetersPerUnit(stage)
    if abs(meters_per_unit - 1.0) > 1e-9:
        fail(f"meters-per-unit is not 1.0: {meters_per_unit}")

    for path, type_name in expected.items():
        prim = stage.GetPrimAtPath(path)
        if not prim or not prim.IsValid():
            fail(f"missing prim: {path}")
        if prim.GetTypeName() != type_name:
            fail(f"{path} expected type {type_name}, got {prim.GetTypeName()}")

    for path, translate in expected_translates.items():
        prim = stage.GetPrimAtPath(path)
        actual = prim_translate(UsdGeom, prim)
        if actual is None:
            fail(f"{path} does not author a translate op")
        rounded = tuple(round(v, 6) for v in actual)
        if rounded != translate:
            fail(f"{path} translate mismatch: expected {translate}, got {rounded}")

    for path, expected_color in expected_colors.items():
        prim = stage.GetPrimAtPath(path)
        color_attr = UsdGeom.Gprim(prim).GetDisplayColorAttr()
        colors = color_attr.Get()
        if not colors:
            fail(f"{path} missing display color")
        actual = tuple(round(v, 6) for v in colors[0])
        if actual != expected_color:
            fail(f"{path} display color mismatch: expected {expected_color}, got {actual}")

    print("OPENUSD: validation passed", flush=True)


def reopen_and_report(Usd, Sdf, UsdGeom):
    text_stage = Usd.Stage.Open(str(USDA_PATH))
    if not text_stage:
        fail(f"failed to reopen USDA stage: {USDA_PATH}")
    text_layer = Sdf.Layer.FindOrOpen(str(USDA_PATH))
    if text_layer is None:
        fail(f"failed to open USDA layer: {USDA_PATH}")
    text_format_id, text_extension, text_args = layer_format_info(text_layer)
    print(
        "OPENUSD: USDA layer format "
        f"id={text_format_id} "
        f"ext={text_extension} "
        f"args={text_args}",
        flush=True,
    )

    binary_stage = Usd.Stage.Open(str(USD_PATH))
    if not binary_stage:
        fail(f"failed to reopen USD stage: {USD_PATH}")
    binary_layer = Sdf.Layer.FindOrOpen(str(USD_PATH))
    if binary_layer is None:
        fail(f"failed to open USD layer: {USD_PATH}")
    binary_format_id, binary_extension, binary_args = layer_format_info(binary_layer)
    print(
        "OPENUSD: USD layer format "
        f"id={binary_format_id} "
        f"ext={binary_extension} "
        f"args={binary_args}",
        flush=True,
    )

    validate_stage(text_stage, UsdGeom)
    validate_stage(binary_stage, UsdGeom)

    validate_layer_file(USDA_PATH, b"#usda", "USDA file")
    validate_layer_file(USD_PATH, b"PXR-USDC", "USD file")


def main() -> int:
    exit_code = 0
    app = SimulationApp(APP_CONFIG)
    print("OPENUSD: SimulationApp initialized", flush=True)

    try:
        from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux

        stage = author_scene(Usd, UsdGeom, UsdLux, Gf)
        stage.GetRootLayer().Save()
        print("OPENUSD: USDA saved", flush=True)

        if not stage.GetRootLayer().Export(str(USD_PATH), "", {"format": "usdc"}):
            fail(f"failed to export binary USD: {USD_PATH}")
        print("OPENUSD: USD saved", flush=True)

        # Release the authored stage before reopening the saved files.
        del stage

        reopen_and_report(Usd, Sdf, UsdGeom)

        for frame in range(1, FRAMES + 1):
            app.update()
            print(f"OPENUSD: frame {frame}/{FRAMES}", flush=True)

        print("OPENUSD: 10 frames completed", flush=True)
    except Exception:
        exit_code = 1
        traceback.print_exc()

    print("OPENUSD: requesting immediate shutdown", flush=True)
    app.close(skip_cleanup=True, exit_code=exit_code)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
