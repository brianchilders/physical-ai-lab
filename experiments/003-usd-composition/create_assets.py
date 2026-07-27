from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import shutil
import sys

from isaacsim import SimulationApp


ROOT = Path(__file__).resolve().parent
ASSET_SOURCE_DIR = ROOT / "assets"
RUNTIME_ASSET_DIR = Path("/mnt/nvme/isaac/experiments/003-usd-composition/assets")
RESULTS_DIR = Path("/mnt/nvme/isaac/experiments/003-usd-composition/results")
HASH_MANIFEST = RESULTS_DIR / "source-asset-hashes.txt"
Sdf = Usd = UsdGeom = None


ASSET_PATHS = [
    ASSET_SOURCE_DIR / "red_cube.usda",
    ASSET_SOURCE_DIR / "blue_sphere.usda",
    ASSET_SOURCE_DIR / "yellow_marker.usda",
    ASSET_SOURCE_DIR / "ground.usda",
    ASSET_SOURCE_DIR / "payload_cluster.usda",
]


def fail(message: str) -> None:
    print(f"COMPOSITION: FAIL: {message}", flush=True)
    raise RuntimeError(message)


def compute_hashes(paths):
    hashes = {}
    for path in paths:
        data = path.read_bytes()
        hashes[path.name] = sha256(data).hexdigest()
    return hashes


def save_hash_manifest(hashes):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with HASH_MANIFEST.open("w", encoding="utf-8") as handle:
        for name in sorted(hashes):
            handle.write(f"{name} {hashes[name]}\n")


def load_manifest():
    if not HASH_MANIFEST.is_file():
        fail(f"missing hash manifest: {HASH_MANIFEST}")
    manifest = {}
    with HASH_MANIFEST.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            name, digest = line.split(maxsplit=1)
            manifest[name] = digest
    return manifest


def validate_manifest(current, expected):
    if current != expected:
        fail(f"source asset hash mismatch: {current!r} != {expected!r}")


def copy_assets_to_runtime():
    RUNTIME_ASSET_DIR.mkdir(parents=True, exist_ok=True)
    for source_path in ASSET_PATHS:
        target_path = RUNTIME_ASSET_DIR / source_path.name
        shutil.copy2(source_path, target_path)


def validate_default_prims(Usd, UsdGeom):
    expected_types = {
        "red_cube.usda": "Cube",
        "blue_sphere.usda": "Sphere",
        "yellow_marker.usda": "Cylinder",
        "ground.usda": "Mesh",
        "payload_cluster.usda": "Xform",
    }
    for source_path in ASSET_PATHS:
        stage = Usd.Stage.Open(str(source_path))
        if not stage:
            fail(f"failed to reopen asset stage: {source_path}")
        default_prim = stage.GetDefaultPrim()
        if not default_prim or not default_prim.IsValid():
            fail(f"missing default prim in {source_path}")
        expected_type = expected_types[source_path.name]
        if default_prim.GetTypeName() != expected_type:
            fail(f"{source_path.name} default prim is not {expected_type}")


def main() -> int:
    simulation_app = SimulationApp({"headless": True})
    exit_code = 0

    print("COMPOSITION: SimulationApp initialized", flush=True)

    try:
        global Sdf, Usd, UsdGeom
        from pxr import Sdf as _Sdf, Usd as _Usd, UsdGeom as _UsdGeom

        Sdf = _Sdf
        Usd = _Usd
        UsdGeom = _UsdGeom

        for source_path in ASSET_PATHS:
            if not source_path.is_file():
                fail(f"missing source asset file: {source_path}")

        source_hashes = compute_hashes(ASSET_PATHS)
        save_hash_manifest(source_hashes)

        copy_assets_to_runtime()
        print("COMPOSITION: reusable assets created", flush=True)

        validate_default_prims(Usd, UsdGeom)
        print("COMPOSITION: asset default prims validated", flush=True)

        validate_manifest(compute_hashes(ASSET_PATHS), source_hashes)
        runtime_hashes = compute_hashes([RUNTIME_ASSET_DIR / path.name for path in ASSET_PATHS])
        if runtime_hashes != source_hashes:
            fail("runtime asset copies do not match the source assets")

        print("COMPOSITION: requesting immediate shutdown", flush=True)
    except Exception:
        exit_code = 1
        import traceback

        traceback.print_exc()
    finally:
        simulation_app.close(skip_cleanup=True, exit_code=exit_code)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
