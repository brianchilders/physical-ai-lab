from __future__ import annotations

import hashlib
import json
import os
import math
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parent
RUNTIME_ROOT = Path(os.environ.get("PHYSICS_FOUNDATIONS_RUNTIME_ROOT", "/mnt/nvme/isaac/experiments/004-physics-foundations"))
OUTPUT_DIR = RUNTIME_ROOT / "output"
RESULTS_DIR = RUNTIME_ROOT / "results"
SCENE_USDA = OUTPUT_DIR / "run-01" / "physics_scene.usda"
SCENE_USD = OUTPUT_DIR / "run-01" / "physics_scene.usd"
RUN_IDS = ("run-01", "run-02")
RUN_OUTPUT_DIRS = {run_id: OUTPUT_DIR / run_id for run_id in RUN_IDS}
RUN_RESULTS_DIRS = {run_id: RESULTS_DIR / run_id for run_id in RUN_IDS}

WORLD_METADATA = {
    "metersPerUnit": 1.0,
    "upAxis": "Z",
    "gravity": [0.0, 0.0, -9.81],
}

SIMULATION_SETTINGS = {
    "stepsPerSecond": 60,
    "maxSteps": 600,
    "settleWindow": 30,
}

TOLERANCES = {
    "finalPositionMeters": 0.001,
    "finalVelocityMetersPerSecond": 0.001,
    "reboundHeightMeters": 0.005,
    "settleStep": 1,
    "contactStep": 1,
}

SCENE_HIERARCHY = [
    "/World",
    "/World/PhysicsScene",
    "/World/Looks",
    "/World/Looks/GroundMaterial",
    "/World/Looks/CubeMaterial",
    "/World/Looks/SphereMaterial",
    "/World/Geometry",
    "/World/Geometry/Ground",
    "/World/Actors",
    "/World/Actors/LowBounceCube",
    "/World/Actors/HighBounceSphere",
]


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_run_dirs(run_id: str) -> tuple[Path, Path]:
    return ensure_dir(RUN_OUTPUT_DIRS[run_id]), ensure_dir(RUN_RESULTS_DIRS[run_id])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def round_vector(values: Iterable[float], places: int = 6) -> list[float]:
    return [round(float(value), places) for value in values]


def vector_to_list(value) -> list[float]:
    return [float(component) for component in value]


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def vector_magnitude(values: Iterable[float]) -> float:
    return math.sqrt(sum(float(component) * float(component) for component in values))
