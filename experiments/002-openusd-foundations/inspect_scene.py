from __future__ import annotations

from pathlib import Path
import sys

from isaacsim import SimulationApp


ROOT = Path(__file__).resolve().parent
USDA_PATH = ROOT / "output" / "openusd_foundations.usda"
USD_PATH = ROOT / "output" / "openusd_foundations.usd"
Sdf = Usd = UsdGeom = None


EXPECTED = {
    "/World": "Xform",
    "/World/Ground": "Mesh",
    "/World/Light": "DistantLight",
    "/World/Lab": "Xform",
    "/World/Lab/RedCube": "Cube",
    "/World/Lab/BlueSphere": "Sphere",
    "/World/Lab/Marker": "Cylinder",
    "/World/Camera": "Camera",
}

EXPECTED_TRANSLATES = {
    "/World/Lab": (0.0, 0.0, 0.0),
    "/World/Lab/RedCube": (-1.0, 0.0, 0.25),
    "/World/Lab/BlueSphere": (1.0, 0.0, 0.25),
    "/World/Lab/Marker": (0.0, 0.9, 0.175),
    "/World/Camera": (0.0, -5.0, 2.5),
}

EXPECTED_COLORS = {
    "/World/Lab/RedCube": (1.0, 0.0, 0.0),
    "/World/Lab/BlueSphere": (0.0, 0.0, 1.0),
    "/World/Lab/Marker": (1.0, 1.0, 0.0),
}


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


def fail(message: str) -> None:
    print(f"OPENUSD_INSPECT: FAIL: {message}", flush=True)
    raise SystemExit(1)


def print_tree(prim, indent=0):
    if not prim or not prim.IsValid():
        return
    prefix = "  " * indent
    print(f"{prefix}{prim.GetPath()} ({prim.GetTypeName()})", flush=True)
    for child in prim.GetChildren():
        print_tree(child, indent + 1)


def prim_translate(prim):
    xform = UsdGeom.Xformable(prim)
    for op in xform.GetOrderedXformOps():
        if op.GetOpType() == UsdGeom.XformOp.TypeTranslate:
            return tuple(op.Get())
    return None


def open_stage(path: Path):
    stage = Usd.Stage.Open(str(path))
    if not stage:
        fail(f"failed to open stage: {path}")
    return stage


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


def main() -> int:
    simulation_app = SimulationApp({"headless": True})
    exit_code = 0

    try:
        global Sdf, Usd, UsdGeom
        from pxr import Sdf as _Sdf, Usd as _Usd, UsdGeom as _UsdGeom
        Sdf = _Sdf
        Usd = _Usd
        UsdGeom = _UsdGeom

        if not USDA_PATH.is_file():
            fail(f"missing stage file: {USDA_PATH}")
        if not USD_PATH.is_file():
            fail(f"missing stage file: {USD_PATH}")

        usda_stage = open_stage(USDA_PATH)
        usd_stage = open_stage(USD_PATH)

        usda_layer = Sdf.Layer.FindOrOpen(str(USDA_PATH))
        if usda_layer is None:
            fail(f"failed to open layer: {USDA_PATH}")
        usd_layer = Sdf.Layer.FindOrOpen(str(USD_PATH))
        if usd_layer is None:
            fail(f"failed to open layer: {USD_PATH}")

        usda_format_id, usda_extension, usda_args = layer_format_info(usda_layer)
        usd_format_id, usd_extension, usd_args = layer_format_info(usd_layer)

        print("OPENUSD_INSPECT: opened USDA", flush=True)
        print("OPENUSD_INSPECT: opened USD", flush=True)
        print(f"OPENUSD_INSPECT: default prim={usda_stage.GetDefaultPrim().GetPath()}", flush=True)
        print(f"OPENUSD_INSPECT: up-axis={UsdGeom.GetStageUpAxis(usda_stage)}", flush=True)
        print(f"OPENUSD_INSPECT: meters-per-unit={UsdGeom.GetStageMetersPerUnit(usda_stage)}", flush=True)
        print(
            "OPENUSD_INSPECT: USDA layer format "
            f"id={usda_format_id} ext={usda_extension} args={usda_args}",
            flush=True,
        )
        print(
            "OPENUSD_INSPECT: USD layer format "
            f"id={usd_format_id} ext={usd_extension} args={usd_args}",
            flush=True,
        )

        for prim in usda_stage.GetPseudoRoot().GetChildren():
            print_tree(prim)

        for path, type_name in EXPECTED.items():
            prim = usda_stage.GetPrimAtPath(path)
            if not prim or not prim.IsValid():
                fail(f"missing prim: {path}")
            if prim.GetTypeName() != type_name:
                fail(f"{path} expected type {type_name}, got {prim.GetTypeName()}")

        if usda_stage.GetDefaultPrim().GetPath().pathString != "/World":
            fail("default prim is not /World")

        if UsdGeom.GetStageUpAxis(usda_stage) != UsdGeom.Tokens.z:
            fail("stage up-axis is not z")

        if abs(UsdGeom.GetStageMetersPerUnit(usda_stage) - 1.0) > 1e-9:
            fail("meters-per-unit is not 1.0")

        for path, expected_translate in EXPECTED_TRANSLATES.items():
            prim = usda_stage.GetPrimAtPath(path)
            actual = prim_translate(prim)
            if actual is None:
                fail(f"{path} does not author a translate op")
            rounded = tuple(round(v, 6) for v in actual)
            if rounded != expected_translate:
                fail(f"{path} translate mismatch: expected {expected_translate}, got {rounded}")

        for path, expected_color in EXPECTED_COLORS.items():
            prim = usda_stage.GetPrimAtPath(path)
            colors = UsdGeom.Gprim(prim).GetDisplayColorAttr().Get()
            if not colors:
                fail(f"{path} missing display color")
            actual = tuple(round(v, 6) for v in colors[0])
            if actual != expected_color:
                fail(f"{path} display color mismatch: expected {expected_color}, got {actual}")

        print("OPENUSD_INSPECT: hierarchy validated", flush=True)
        print("OPENUSD_INSPECT: transforms validated", flush=True)
        print("OPENUSD_INSPECT: colors validated", flush=True)
        print("OPENUSD_INSPECT: inspection passed", flush=True)
        return 0
    finally:
        simulation_app.close(skip_cleanup=True, exit_code=exit_code)


if __name__ == "__main__":
    raise SystemExit(main())
