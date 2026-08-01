from __future__ import annotations

import csv
import os
import json
import math
import sys
import traceback
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from isaacsim import SimulationApp

simulation_app = SimulationApp({"headless": True})
print("PHYSICS_INSPECT: SimulationApp initialized", flush=True)

from pxr import PhysxSchema, Usd, UsdGeom, UsdPhysics, UsdShade

print("PHYSICS_INSPECT: pxr runtime imports loaded", flush=True)

ROOT = Path(__file__).resolve().parent
from physics_common import (  # noqa: E402
    RESULTS_DIR,
    RUN_IDS,
    RUN_OUTPUT_DIRS,
    RUN_RESULTS_DIRS,
    SCENE_USDA,
    SCENE_USD,
    SIMULATION_SETTINGS,
    TOLERANCES,
    WORLD_METADATA,
    read_json,
    sha256_file,
    vector_magnitude,
)

EXPECTED_IMAGE_REF = "nvcr.io/nvidia/isaac-sim:6.0.1"
CANONICAL_RUNTIME_ROOT = Path("/mnt/nvme/isaac/experiments/004-physics-foundations")
EXPECTED_STEPS = SIMULATION_SETTINGS["maxSteps"]
EXPECTED_COMPLETED_STEPS = 433
EXPECTED_ROWS = EXPECTED_COMPLETED_STEPS * 2
EXPECTED_DT = 1.0 / float(SIMULATION_SETTINGS["stepsPerSecond"])
TRACE_TOLERANCE = 1e-6
ENERGY_TOLERANCE = 1e-5
POSITION_TOLERANCE = 1e-6
VELOCITY_TOLERANCE = 1e-6
RUNTIME_DIAGNOSTIC_TOLERANCE = TOLERANCES["finalVelocityMetersPerSecond"]
CONTACT_EVENT_TYPES = {"contact_found", "contact_persists", "contact_lost", "contact_unknown"}
BODY_SPECS = {
    "cube": {"path": "/World/Actors/LowBounceCube", "mass": 2.0},
    "sphere": {"path": "/World/Actors/HighBounceSphere", "mass": 1.0},
}
EXPECTED_STATE_SOURCES = {
    "pose_velocity": "finite difference of runtime world positions across completed steps",
    "runtime": {
        "angular_velocity": "omni.physics.tensors.RigidBodyView.get_velocities()",
        "linear_velocity": "omni.physics.tensors.RigidBodyView.get_velocities()",
        "physics_simulation_view": "isaacsim.core.simulation_manager.SimulationManager.get_physics_simulation_view()",
        "pose": "omni.physics.tensors.RigidBodyView.get_transforms()",
        "sleep": "omni.physx.IPhysxSimulation.is_sleeping(stage_id, body_path)",
    },
    "usd_sampled": {
        "angular_velocity": "UsdPhysics.RigidBodyAPI.GetAngularVelocityAttr()",
        "linear_velocity": "UsdPhysics.RigidBodyAPI.GetVelocityAttr()",
        "pose": "UsdGeom.Xformable translation ops and rigid-body authored attrs (diagnostic only)",
    },
}
EXPECTED_POLICY_STRINGS = {
    "authoritative_runtime_pose_source": "omni.physics.tensors.RigidBodyView.get_transforms()",
    "authoritative_runtime_velocity_source": "omni.physics.tensors.RigidBodyView.get_velocities()",
    "physics_simulation_view_source": "isaacsim.core.simulation_manager.SimulationManager.get_physics_simulation_view()",
    "settlement_velocity_source": "omni.physics.tensors.RigidBodyView.get_velocities()",
    "sleep_state_source": "omni.physx.IPhysxSimulation.is_sleeping(stage_id, body_path)",
    "angular_speed_formula": "sqrt(wx**2 + wy**2 + wz**2)",
    "image_ref": EXPECTED_IMAGE_REF,
}
EXPECTED_STAGE_HASHES = {
    "usda": "d7254cbc33187e42a5137527c682518a4e39db7691b64d93d18ca3506df42e48",
    "usd": "eccc945fc4dc26d3b688715adce7f096b1aff40b6f834e503bf473fd6731f599",
}


class InspectionFailure(RuntimeError):
    pass


@dataclass
class RunArtifacts:
    run_id: str
    summary_path: Path
    trace_path: Path
    summary: dict[str, Any]
    rows: list[dict[str, str]]
    sizes: dict[str, int]
    hashes: dict[str, str]
    stage_paths: dict[str, Path]
    stage_hashes: dict[str, str]


@dataclass
class RunValidation:
    run_id: str
    summary_file: dict[str, Any]
    trace: dict[str, Any]
    events: dict[str, Any]
    sleep: dict[str, Any]
    energy: dict[str, Any]
    final_state: dict[str, Any]
    final_30_step_ranges: dict[str, Any]


def fail(message: str) -> None:
    raise InspectionFailure(message)


def flush_output_streams() -> None:
    sys.stdout.flush()
    sys.stderr.flush()


def verify_success_gate(report: dict[str, Any], report_path: Path) -> None:
    if report.get("status") != "passed":
        fail(f"formal inspection did not pass: {report.get('failure_reason')!r}")
    if report_path != RESULTS_DIR / "summary.md":
        fail(f"unexpected inspection report path: {report_path}")
    if not report_path.is_file():
        fail(f"missing inspection report on disk: {report_path}")
    if report.get("stage_integrity", {}).get("stage_identical") is not True:
        fail("canonical stage hashes do not match")
    if report.get("stage", {}).get("run-01", {}).get("usda_hash") != EXPECTED_STAGE_HASHES["usda"]:
        fail("pre- and post-inspection USDA hashes do not match")
    if report.get("stage", {}).get("run-01", {}).get("usd_hash") != EXPECTED_STAGE_HASHES["usd"]:
        fail("pre- and post-inspection USD hashes do not match")
    if report.get("stage", {}).get("run-02", {}).get("usda_hash") != EXPECTED_STAGE_HASHES["usda"]:
        fail("run-02 USDA hash does not match expected value")
    if report.get("stage", {}).get("run-02", {}).get("usd_hash") != EXPECTED_STAGE_HASHES["usd"]:
        fail("run-02 USD hash does not match expected value")
    if report.get("stage", {}).get("report_hash") != sha256_file(report_path):
        fail("inspection report hash changed after write")
    if report.get("stage", {}).get("report_size") != report_path.stat().st_size:
        fail("inspection report size changed after write")
    required_run_keys = {
        "summary_file",
        "trace",
        "contact",
        "sleep",
        "energy",
        "settling",
        "events",
        "summary_to_trace",
        "final_30_step_ranges",
    }
    for run_id in RUN_IDS:
        run = report.get("runs", {}).get(run_id)
        if run is None:
            fail(f"missing run report for {run_id}")
        missing = sorted(required_run_keys - set(run))
        if missing:
            fail(f"missing required run report sections for {run_id}: {missing}")
        trace = run["trace"]
        if trace.get("rows") != EXPECTED_ROWS:
            fail(f"unexpected CSV row count for {run_id}: {trace.get('rows')!r}")
        if trace.get("steps") != EXPECTED_COMPLETED_STEPS:
            fail(f"unexpected completed step count for {run_id}: {trace.get('steps')!r}")
        if trace.get("time_continuity", {}).get("dt") != EXPECTED_DT:
            fail(f"unexpected timestep for {run_id}: {trace.get('time_continuity', {}).get('dt')!r}")
        if trace.get("time_continuity", {}).get("final_duration_s") != round(EXPECTED_COMPLETED_STEPS * EXPECTED_DT, 6):
            fail(f"unexpected simulation duration for {run_id}: {trace.get('time_continuity', {}).get('final_duration_s')!r}")
        if run.get("settling", {}).get("run_settle_step") != EXPECTED_COMPLETED_STEPS:
            fail(f"unexpected shared settle step for {run_id}: {run.get('settling', {}).get('run_settle_step')!r}")
        expected_completion = {
            "cube_contacted_ground": True,
            "cube_settled": True,
            "sphere_contacted_ground": True,
            "sphere_rebound_detected": True,
            "sphere_settled": True,
            "unmet_conditions": [],
        }
        if run.get("summary_to_trace", {}).get("completion") != expected_completion:
            fail(f"completion summary mismatch for {run_id}")


def to_float(value: Any) -> float:
    if value in (None, ""):
        return float("nan")
    return float(value)


def finite(value: Any, field: str, run_id: str, step: int | None = None, actor: str | None = None) -> float:
    parsed = to_float(value)
    if not math.isfinite(parsed):
        where = f" run={run_id}"
        if step is not None:
            where += f" step={step}"
        if actor is not None:
            where += f" actor={actor}"
        fail(f"nonfinite value in field={field}{where}: {value!r}")
    return parsed


def close_enough(actual: float, expected: float, tolerance: float) -> bool:
    return abs(float(actual) - float(expected)) <= tolerance


def parse_bool_field(value: str, field: str, run_id: str, step: int, actor: str) -> int:
    if value not in {"0", "1"}:
        fail(f"invalid boolean field {field} in run={run_id} step={step} actor={actor}: {value!r}")
    return int(value)


def format_float(value: float, places: int = 6) -> str:
    text = f"{float(value):.{places}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def vector_field(row: dict[str, str], prefix: str, suffix: str = "") -> tuple[float, float, float]:
    return (
        to_float(row[f"{prefix}x{suffix}"]),
        to_float(row[f"{prefix}y{suffix}"]),
        to_float(row[f"{prefix}z{suffix}"]),
    )


def magnitude_3(row: dict[str, str], prefix: str, suffix: str = "") -> float:
    return vector_magnitude(vector_field(row, prefix, suffix))


def md_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return lines


def extract_expected_hierarchy_lines() -> list[str]:
    path = ROOT / "expected-hierarchy.txt"
    lines: list[str] = []
    in_block = False
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        if line.strip().startswith("```"):
            in_block = not in_block
            continue
        if in_block and line.strip():
            lines.append(line)
    return lines


def collect_hierarchy_lines(stage: Usd.Stage) -> list[str]:
    default_prim = stage.GetDefaultPrim()
    if not default_prim or not default_prim.IsValid():
        fail("stage has no valid default prim")

    lines: list[str] = []

    def walk(prim, depth: int) -> None:
        lines.append(f"{'  ' * depth}{prim.GetPath()} ({prim.GetTypeName()})")
        for child in prim.GetChildren():
            walk(child, depth + 1)

    walk(default_prim, 0)
    return lines


def validate_header(path: Path, expected_prefix: bytes, label: str) -> None:
    with path.open("rb") as handle:
        header = handle.read(len(expected_prefix))
    if header != expected_prefix:
        fail(f"{label} has unexpected signature: {header!r}")


def load_run_artifacts(run_id: str) -> RunArtifacts:
    run_results_dir = RUN_RESULTS_DIRS[run_id]
    run_output_dir = RUN_OUTPUT_DIRS[run_id]
    summary_path = run_results_dir / "summary.json"
    trace_path = run_results_dir / "step_metrics.csv"
    stage_paths = {
        "usda": run_output_dir / "physics_scene.usda",
        "usd": run_output_dir / "physics_scene.usd",
    }
    for label, path in (("summary", summary_path), ("trace", trace_path), ("USDA", stage_paths["usda"]), ("USD", stage_paths["usd"])):
        if not path.is_file():
            fail(f"missing {label} artifact for {run_id}: {path}")

    with trace_path.open("r", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    return RunArtifacts(
        run_id=run_id,
        summary_path=summary_path,
        trace_path=trace_path,
        summary=read_json(summary_path),
        rows=rows,
        sizes={
            "summary": summary_path.stat().st_size,
            "trace": trace_path.stat().st_size,
            "usda": stage_paths["usda"].stat().st_size,
            "usd": stage_paths["usd"].stat().st_size,
        },
        hashes={
            "summary": sha256_file(summary_path),
            "trace": sha256_file(trace_path),
            "usda": sha256_file(stage_paths["usda"]),
            "usd": sha256_file(stage_paths["usd"]),
        },
        stage_paths=stage_paths,
        stage_hashes={
            "usda": sha256_file(stage_paths["usda"]),
            "usd": sha256_file(stage_paths["usd"]),
        },
    )


def validate_stage_metadata(stage: Usd.Stage, run_id: str) -> dict[str, Any]:
    default_prim = stage.GetDefaultPrim()
    if not default_prim or default_prim.GetPath().pathString != "/World":
        fail(f"[{run_id}] default prim is not /World")
    if UsdGeom.GetStageUpAxis(stage) != UsdGeom.Tokens.z:
        fail(f"[{run_id}] stage up-axis is not Z")
    meters_per_unit = UsdGeom.GetStageMetersPerUnit(stage)
    if abs(meters_per_unit - 1.0) > 1e-9:
        fail(f"[{run_id}] metersPerUnit mismatch: {meters_per_unit}")

    scene = UsdPhysics.Scene.Get(stage, "/World/PhysicsScene")
    if not scene:
        fail(f"[{run_id}] missing /World/PhysicsScene")
    physics_scene_prim = scene.GetPrim()
    if not physics_scene_prim or physics_scene_prim.GetTypeName() != "PhysicsScene":
        fail(f"[{run_id}] /World/PhysicsScene type mismatch")

    physx_scene = PhysxSchema.PhysxSceneAPI(physics_scene_prim)
    if not physx_scene:
        fail(f"[{run_id}] missing PhysxSceneAPI on /World/PhysicsScene")

    solver_type = physx_scene.GetSolverTypeAttr().Get()
    broadphase_type = physx_scene.GetBroadphaseTypeAttr().Get()
    if solver_type != PhysxSchema.Tokens.TGS:
        fail(f"[{run_id}] solver token mismatch: {solver_type!r}")
    if broadphase_type != PhysxSchema.Tokens.MBP:
        fail(f"[{run_id}] broadphase token mismatch: {broadphase_type!r}")
    if bool(physx_scene.GetEnableCCDAttr().Get()) is not True:
        fail(f"[{run_id}] CCD not authored true")
    if bool(physx_scene.GetEnableStabilizationAttr().Get()) is not True:
        fail(f"[{run_id}] stabilization not authored true")
    if bool(physx_scene.GetEnableGPUDynamicsAttr().Get()) is not False:
        fail(f"[{run_id}] GPU dynamics not authored false")

    enhanced_attr = None
    if hasattr(physx_scene, "GetEnableEnhancedDeterminismAttr"):
        enhanced_attr = physx_scene.GetEnableEnhancedDeterminismAttr()
    if enhanced_attr is None or enhanced_attr.Get() is None:
        fail(f"[{run_id}] enhanced determinism attribute is missing")
    if bool(enhanced_attr.Get()) is not True:
        fail(f"[{run_id}] enhanced determinism not authored true")

    gravity = tuple(float(v) for v in scene.GetGravityDirectionAttr().Get())
    magnitude = float(scene.GetGravityMagnitudeAttr().Get())
    if tuple(round(v, 6) for v in gravity) != (0.0, 0.0, -1.0):
        fail(f"[{run_id}] gravity direction mismatch: {gravity}")
    if abs(magnitude - 9.81) > 1e-6:
        fail(f"[{run_id}] gravity magnitude mismatch: {magnitude}")

    expectations = {
        "/World": "Xform",
        "/World/PhysicsScene": "PhysicsScene",
        "/World/Looks": "Scope",
        "/World/Looks/GroundMaterial": "Material",
        "/World/Looks/CubeMaterial": "Material",
        "/World/Looks/SphereMaterial": "Material",
        "/World/Geometry": "Xform",
        "/World/Geometry/Ground": "Mesh",
        "/World/Actors": "Xform",
        "/World/Actors/LowBounceCube": "Cube",
        "/World/Actors/HighBounceSphere": "Sphere",
    }
    applied_api_report: dict[str, list[str]] = {}
    for path, type_name in expectations.items():
        prim = stage.GetPrimAtPath(path)
        if not prim or not prim.IsValid():
            fail(f"[{run_id}] missing prim: {path}")
        if prim.GetTypeName() != type_name:
            fail(f"[{run_id}] type mismatch at {path}: {prim.GetTypeName()} != {type_name}")
        applied_api_report[path] = [str(schema) for schema in prim.GetAppliedSchemas()]

    ground = stage.GetPrimAtPath("/World/Geometry/Ground")
    cube = stage.GetPrimAtPath("/World/Actors/LowBounceCube")
    sphere = stage.GetPrimAtPath("/World/Actors/HighBounceSphere")
    ground_material = stage.GetPrimAtPath("/World/Looks/GroundMaterial")
    cube_material = stage.GetPrimAtPath("/World/Looks/CubeMaterial")
    sphere_material = stage.GetPrimAtPath("/World/Looks/SphereMaterial")

    required_apis = {
        "/World/PhysicsScene": (PhysxSchema.PhysxSceneAPI,),
        "/World/Looks/GroundMaterial": (UsdPhysics.MaterialAPI, PhysxSchema.PhysxMaterialAPI),
        "/World/Looks/CubeMaterial": (UsdPhysics.MaterialAPI, PhysxSchema.PhysxMaterialAPI),
        "/World/Looks/SphereMaterial": (UsdPhysics.MaterialAPI, PhysxSchema.PhysxMaterialAPI),
        "/World/Geometry/Ground": (UsdPhysics.CollisionAPI, UsdPhysics.MeshCollisionAPI, UsdShade.MaterialBindingAPI),
        "/World/Actors/LowBounceCube": (UsdPhysics.CollisionAPI, UsdPhysics.RigidBodyAPI, UsdPhysics.MassAPI, PhysxSchema.PhysxContactReportAPI, UsdShade.MaterialBindingAPI),
        "/World/Actors/HighBounceSphere": (UsdPhysics.CollisionAPI, UsdPhysics.RigidBodyAPI, UsdPhysics.MassAPI, PhysxSchema.PhysxContactReportAPI, UsdShade.MaterialBindingAPI),
    }
    for path, apis in required_apis.items():
        prim = stage.GetPrimAtPath(path)
        for api in apis:
            if not prim.HasAPI(api):
                fail(f"[{run_id}] missing applied API {api.__name__} on {path}")

    for prim, expected_mass in ((cube, 2.0), (sphere, 1.0)):
        mass = float(UsdPhysics.MassAPI(prim).GetMassAttr().Get())
        if abs(mass - expected_mass) > 1e-9:
            fail(f"[{run_id}] mass mismatch on {prim.GetPath()}: {mass} != {expected_mass}")

    if tuple(round(v, 6) for v in _translate(UsdGeom, cube)) != (-1.0, 0.0, 0.26):
        fail(f"[{run_id}] cube translate mismatch")
    if tuple(round(v, 6) for v in _translate(UsdGeom, sphere)) != (1.0, 0.0, 1.75):
        fail(f"[{run_id}] sphere translate mismatch")

    cube_velocity = tuple(float(v) for v in UsdPhysics.RigidBodyAPI(cube).GetVelocityAttr().Get())
    cube_angular_velocity = tuple(float(v) for v in UsdPhysics.RigidBodyAPI(cube).GetAngularVelocityAttr().Get())
    sphere_velocity = tuple(float(v) for v in UsdPhysics.RigidBodyAPI(sphere).GetVelocityAttr().Get())
    sphere_angular_velocity = tuple(float(v) for v in UsdPhysics.RigidBodyAPI(sphere).GetAngularVelocityAttr().Get())
    if tuple(round(v, 6) for v in cube_velocity) != (1.5, 0.0, 0.0):
        fail(f"[{run_id}] cube velocity mismatch: {cube_velocity}")
    if tuple(round(v, 6) for v in cube_angular_velocity) != (0.0, 0.0, 0.0):
        fail(f"[{run_id}] cube angular velocity mismatch: {cube_angular_velocity}")
    if tuple(round(v, 6) for v in sphere_velocity) != (0.0, 0.0, 0.0):
        fail(f"[{run_id}] sphere velocity mismatch: {sphere_velocity}")
    if tuple(round(v, 6) for v in sphere_angular_velocity) != (0.0, 0.0, 0.0):
        fail(f"[{run_id}] sphere angular velocity mismatch: {sphere_angular_velocity}")

    validate_binding(ground, "/World/Looks/GroundMaterial")
    validate_binding(cube, "/World/Looks/CubeMaterial")
    validate_binding(sphere, "/World/Looks/SphereMaterial")

    for prim, static_friction, dynamic_friction, restitution in (
        (ground_material, 0.9, 0.8, 0.0),
        (cube_material, 0.85, 0.75, 0.05),
        (sphere_material, 0.05, 0.03, 0.85),
    ):
        api = UsdPhysics.MaterialAPI(prim)
        if abs(float(api.GetStaticFrictionAttr().Get()) - static_friction) > 1e-6:
            fail(f"[{run_id}] static friction mismatch on {prim.GetPath()}")
        if abs(float(api.GetDynamicFrictionAttr().Get()) - dynamic_friction) > 1e-6:
            fail(f"[{run_id}] dynamic friction mismatch on {prim.GetPath()}")
        if abs(float(api.GetRestitutionAttr().Get()) - restitution) > 1e-6:
            fail(f"[{run_id}] restitution mismatch on {prim.GetPath()}")

    if tuple(round(v, 6) for v in stage.GetPrimAtPath("/World/Geometry/Ground").GetAttribute("points").Get()[0]) != (-5.0, -5.0, 0.0):
        fail(f"[{run_id}] ground mesh points mismatch")

    return {
        "default_prim": str(default_prim.GetPath()),
        "metersPerUnit": meters_per_unit,
        "upAxis": str(UsdGeom.GetStageUpAxis(stage)),
        "gravity": list(gravity),
        "gravity_magnitude": magnitude,
        "hierarchy_lines": collect_hierarchy_lines(stage),
        "expected_hierarchy_lines": extract_expected_hierarchy_lines(),
        "applied_schemas": applied_api_report,
        "physics_scene": {
            "solver": str(solver_type),
            "broadphase": str(broadphase_type),
            "enableCCD": bool(physx_scene.GetEnableCCDAttr().Get()),
            "enableStabilization": bool(physx_scene.GetEnableStabilizationAttr().Get()),
            "enableGPUDynamics": bool(physx_scene.GetEnableGPUDynamicsAttr().Get()),
            "enableEnhancedDeterminism": bool(enhanced_attr.Get()),
        },
        "material_bindings": {
            "/World/Geometry/Ground": validate_binding_report(stage.GetPrimAtPath("/World/Geometry/Ground")),
            "/World/Actors/LowBounceCube": validate_binding_report(cube),
            "/World/Actors/HighBounceSphere": validate_binding_report(sphere),
        },
    }


def _translate(UsdGeom_module, prim) -> tuple[float, float, float]:
    xform = UsdGeom_module.Xformable(prim)
    for op in xform.GetOrderedXformOps():
        if op.GetOpType() == UsdGeom_module.XformOp.TypeTranslate:
            value = op.Get()
            return tuple(float(component) for component in value)
    return (0.0, 0.0, 0.0)


def validate_binding(prim, material_path: str) -> None:
    binding_rel = prim.GetRelationship("material:binding:physics")
    if not binding_rel or not binding_rel.IsValid():
        fail(f"missing physics material binding on {prim.GetPath()}")
    if binding_rel.GetName() != "material:binding:physics":
        fail(f"unexpected physics material binding relationship on {prim.GetPath()}: {binding_rel.GetName()}")
    targets = [target.pathString for target in binding_rel.GetTargets()]
    if material_path not in targets:
        fail(f"physics material binding on {prim.GetPath()} does not target {material_path}")


def validate_binding_report(prim) -> dict[str, Any]:
    binding_rel = prim.GetRelationship("material:binding:physics")
    return {
        "relationship": binding_rel.GetName(),
        "targets": [target.pathString for target in binding_rel.GetTargets()],
    }


def validate_file_inventory(artifacts: RunArtifacts) -> dict[str, Any]:
    if artifacts.summary.get("run_id") != artifacts.run_id:
        fail(f"summary run_id mismatch for {artifacts.run_id}: {artifacts.summary.get('run_id')!r}")
    if artifacts.summary.get("status") != "passed":
        fail(f"summary status is not passed for {artifacts.run_id}: {artifacts.summary.get('status')!r}")
    if artifacts.summary.get("pass_fail") != "pass":
        fail(f"summary pass_fail is not pass for {artifacts.run_id}: {artifacts.summary.get('pass_fail')!r}")

    stage_info = artifacts.summary.get("stage", {})
    expected_stage_fields = {
        "canonical_usd",
        "canonical_usda",
        "run_output_dir",
        "run_results_dir",
        "snapshot_usd",
        "snapshot_usda",
    }
    if not expected_stage_fields.issubset(stage_info):
        missing = sorted(expected_stage_fields.difference(stage_info))
        fail(f"summary stage block missing fields for {artifacts.run_id}: {missing}")

    if stage_info.get("run_results_dir") != str(CANONICAL_RUNTIME_ROOT / "results" / artifacts.run_id):
        fail(f"summary run_results_dir mismatch for {artifacts.run_id}")
    if stage_info.get("run_output_dir") != str(CANONICAL_RUNTIME_ROOT / "output" / artifacts.run_id):
        fail(f"summary run_output_dir mismatch for {artifacts.run_id}")
    if stage_info.get("snapshot_usda") != str(CANONICAL_RUNTIME_ROOT / "output" / artifacts.run_id / "physics_scene.usda"):
        fail(f"summary snapshot_usda mismatch for {artifacts.run_id}")
    if stage_info.get("snapshot_usd") != str(CANONICAL_RUNTIME_ROOT / "output" / artifacts.run_id / "physics_scene.usd"):
        fail(f"summary snapshot_usd mismatch for {artifacts.run_id}")

    if artifacts.summary.get("image_ref") != EXPECTED_IMAGE_REF:
        fail(f"image_ref mismatch for {artifacts.run_id}")
    if artifacts.summary.get("simulation") != {
        "stepsPerSecond": SIMULATION_SETTINGS["stepsPerSecond"],
        "maxSteps": SIMULATION_SETTINGS["maxSteps"],
        "settleWindow": SIMULATION_SETTINGS["settleWindow"],
    }:
        fail(f"simulation settings mismatch for {artifacts.run_id}")
    if artifacts.summary.get("world") != WORLD_METADATA:
        fail(f"world metadata mismatch in summary for {artifacts.run_id}")

    if artifacts.summary.get("thresholds") != {
        "final_position_m": TOLERANCES["finalPositionMeters"],
        "final_velocity_mps": TOLERANCES["finalVelocityMetersPerSecond"],
        "rebound_height_m": TOLERANCES["reboundHeightMeters"],
        "settle_step": TOLERANCES["settleStep"],
        "contact_step": TOLERANCES["contactStep"],
    }:
        fail(f"threshold block mismatch for {artifacts.run_id}")

    if artifacts.summary.get("angular_speed_formula") != "sqrt(wx**2 + wy**2 + wz**2)":
        fail(f"angular speed formula mismatch for {artifacts.run_id}")
    if artifacts.summary.get("authoritative_runtime_pose_source") != EXPECTED_POLICY_STRINGS["authoritative_runtime_pose_source"]:
        fail(f"runtime pose source mismatch for {artifacts.run_id}")
    if artifacts.summary.get("authoritative_runtime_velocity_source") != EXPECTED_POLICY_STRINGS["authoritative_runtime_velocity_source"]:
        fail(f"runtime velocity source mismatch for {artifacts.run_id}")
    if artifacts.summary.get("physics_simulation_view_source") != EXPECTED_POLICY_STRINGS["physics_simulation_view_source"]:
        fail(f"simulation view source mismatch for {artifacts.run_id}")
    if artifacts.summary.get("settlement_velocity_source") != EXPECTED_POLICY_STRINGS["settlement_velocity_source"]:
        fail(f"settlement velocity source mismatch for {artifacts.run_id}")
    if artifacts.summary.get("sleep_state_source") != EXPECTED_POLICY_STRINGS["sleep_state_source"]:
        fail(f"sleep state source mismatch for {artifacts.run_id}")

    expected_state_sources = EXPECTED_STATE_SOURCES
    if artifacts.summary.get("state_sources") != expected_state_sources:
        fail(f"state source policy mismatch for {artifacts.run_id}")

    artifact_hashes = artifacts.summary.get("artifact_hashes", {})
    if artifact_hashes.get("trace_csv") != artifacts.hashes["trace"]:
        fail(f"trace hash mismatch for {artifacts.run_id}")
    if artifact_hashes.get("snapshot_usda") != artifacts.stage_hashes["usda"]:
        fail(f"snapshot_usda hash mismatch for {artifacts.run_id}")
    if artifact_hashes.get("snapshot_usd") != artifacts.stage_hashes["usd"]:
        fail(f"snapshot_usd hash mismatch for {artifacts.run_id}")

    if artifacts.summary.get("completed_steps") != EXPECTED_COMPLETED_STEPS:
        fail(f"completed_steps mismatch for {artifacts.run_id}")
    if artifacts.summary.get("failure_reason") not in (None, ""):
        fail(f"failure_reason unexpectedly populated for {artifacts.run_id}")

    return {
        "sizes": artifacts.sizes,
        "hashes": artifacts.hashes,
        "artifact_hashes": artifact_hashes,
        "stage": stage_info,
    }


def validate_trace_continuity(artifacts: RunArtifacts) -> dict[str, Any]:
    rows = artifacts.rows
    if not rows:
        fail(f"empty trace file for {artifacts.run_id}")
    if len(rows) != EXPECTED_ROWS:
        fail(f"row count mismatch for {artifacts.run_id}: {len(rows)} != {EXPECTED_ROWS}")

    required_fields = {
        "run_id",
        "step_index",
        "sim_time_s",
        "actor",
        "position_x_m",
        "position_y_m",
        "position_z_m",
        "orientation_x",
        "orientation_y",
        "orientation_z",
        "orientation_w",
        "usd_sampled_linear_velocity_x_mps",
        "usd_sampled_linear_velocity_y_mps",
        "usd_sampled_linear_velocity_z_mps",
        "usd_sampled_vertical_velocity_mps",
        "usd_sampled_total_speed_mps",
        "usd_sampled_planar_speed_mps",
        "usd_sampled_angular_velocity_x_rad_s",
        "usd_sampled_angular_velocity_y_rad_s",
        "usd_sampled_angular_velocity_z_rad_s",
        "usd_sampled_angular_speed_rad_s",
        "runtime_linear_velocity_x_mps",
        "runtime_linear_velocity_y_mps",
        "runtime_linear_velocity_z_mps",
        "runtime_vertical_velocity_mps",
        "runtime_total_speed_mps",
        "runtime_planar_speed_mps",
        "runtime_angular_velocity_x_rad_s",
        "runtime_angular_velocity_y_rad_s",
        "runtime_angular_velocity_z_rad_s",
        "runtime_angular_speed_rad_s",
        "pose_linear_velocity_x_mps",
        "pose_linear_velocity_y_mps",
        "pose_linear_velocity_z_mps",
        "pose_speed_mps",
        "sleeping",
        "contact_state",
        "contact_found",
        "contact_persists",
        "contact_lost",
        "contact_active",
        "settle_counter",
        "rebound_state",
        "usd_sampled_kinetic_energy_j",
        "usd_sampled_potential_energy_j",
        "usd_sampled_total_mechanical_energy_j",
        "runtime_kinetic_energy_j",
        "runtime_potential_energy_j",
        "runtime_total_mechanical_energy_j",
        "cube_px",
        "cube_py",
        "cube_pz",
        "cube_orientation_x",
        "cube_orientation_y",
        "cube_orientation_z",
        "cube_orientation_w",
        "cube_usd_sampled_vx",
        "cube_usd_sampled_vy",
        "cube_usd_sampled_vz",
        "cube_usd_sampled_speed_mps",
        "cube_usd_sampled_planar_speed_mps",
        "cube_usd_sampled_vertical_speed_mps",
        "cube_usd_sampled_wx_rad_s",
        "cube_usd_sampled_wy_rad_s",
        "cube_usd_sampled_wz_rad_s",
        "cube_usd_sampled_angular_speed_rad_s",
        "cube_runtime_vx",
        "cube_runtime_vy",
        "cube_runtime_vz",
        "cube_runtime_speed_mps",
        "cube_runtime_planar_speed_mps",
        "cube_runtime_vertical_speed_mps",
        "cube_runtime_wx_rad_s",
        "cube_runtime_wy_rad_s",
        "cube_runtime_wz_rad_s",
        "cube_runtime_angular_speed_rad_s",
        "cube_pose_vx",
        "cube_pose_vy",
        "cube_pose_vz",
        "cube_pose_speed_mps",
        "cube_sleeping",
        "cube_contact_found",
        "cube_contact_persists",
        "cube_contact_lost",
        "sphere_px",
        "sphere_py",
        "sphere_pz",
        "sphere_orientation_x",
        "sphere_orientation_y",
        "sphere_orientation_z",
        "sphere_orientation_w",
        "sphere_usd_sampled_vx",
        "sphere_usd_sampled_vy",
        "sphere_usd_sampled_vz",
        "sphere_usd_sampled_speed_mps",
        "sphere_usd_sampled_planar_speed_mps",
        "sphere_usd_sampled_vertical_speed_mps",
        "sphere_usd_sampled_wx_rad_s",
        "sphere_usd_sampled_wy_rad_s",
        "sphere_usd_sampled_wz_rad_s",
        "sphere_usd_sampled_angular_speed_rad_s",
        "sphere_runtime_vx",
        "sphere_runtime_vy",
        "sphere_runtime_vz",
        "sphere_runtime_speed_mps",
        "sphere_runtime_planar_speed_mps",
        "sphere_runtime_vertical_speed_mps",
        "sphere_runtime_wx_rad_s",
        "sphere_runtime_wy_rad_s",
        "sphere_runtime_wz_rad_s",
        "sphere_runtime_angular_speed_rad_s",
        "sphere_pose_vx",
        "sphere_pose_vy",
        "sphere_pose_vz",
        "sphere_pose_speed_mps",
        "sphere_sleeping",
        "sphere_contact_found",
        "sphere_contact_persists",
        "sphere_contact_lost",
        "sphere_rebounded",
        "run_settled",
    }
    if not required_fields.issubset(rows[0].keys()):
        missing = sorted(required_fields.difference(rows[0].keys()))
        fail(f"missing required CSV column: {missing[0]}")

    by_step: dict[int, dict[str, dict[str, str]]] = defaultdict(dict)
    actors = {"cube", "sphere"}
    first_step_optional_fields = {
        "pose_linear_velocity_x_mps",
        "pose_linear_velocity_y_mps",
        "pose_linear_velocity_z_mps",
        "pose_speed_mps",
        "cube_pose_vx",
        "cube_pose_vy",
        "cube_pose_vz",
        "cube_pose_speed_mps",
        "sphere_pose_vx",
        "sphere_pose_vy",
        "sphere_pose_vz",
        "sphere_pose_speed_mps",
    }
    for row in rows:
        if row.get("run_id") != artifacts.run_id:
            fail(f"run_id mismatch in trace row for {artifacts.run_id}: {row.get('run_id')!r}")
        actor = row["actor"]
        if actor not in actors:
            fail(f"unexpected actor in trace for {artifacts.run_id}: {actor!r}")
        step = int(row["step_index"])
        if step in by_step and actor in by_step[step]:
            fail(f"duplicate step/actor row in trace for {artifacts.run_id}: step={step} actor={actor}")
        by_step[step][actor] = row

        for field in row:
            if field in {"run_id", "actor", "contact_state"}:
                continue
            if step == 1 and field in first_step_optional_fields and row[field] == "":
                continue
            if field.endswith(("sleeping", "found", "persists", "lost", "active", "rebounded", "run_settled", "contact_active")):
                parse_bool_field(row[field], field, artifacts.run_id, step, actor)
            else:
                finite(row[field], field, artifacts.run_id, step, actor)

    expected_steps = list(range(1, EXPECTED_COMPLETED_STEPS + 1))
    actual_steps = sorted(by_step)
    if actual_steps != expected_steps:
        missing = [step for step in expected_steps if step not in by_step]
        extra = [step for step in actual_steps if step not in expected_steps]
        fail(f"step continuity mismatch for {artifacts.run_id}: missing={missing[:5]} extra={extra[:5]}")

    contiguous_times: dict[int, float] = {}
    for step in expected_steps:
        step_rows = by_step[step]
        if set(step_rows) != actors:
            fail(f"actor coverage mismatch for {artifacts.run_id} step={step}: {sorted(step_rows)}")
        times = {to_float(row["sim_time_s"]) for row in step_rows.values()}
        if len(times) != 1:
            fail(f"inconsistent simulation time for {artifacts.run_id} step={step}: {times}")
        sim_time = times.pop()
        expected_time = step * EXPECTED_DT
        if abs(sim_time - expected_time) > 5e-6:
            fail(f"simulation time mismatch for {artifacts.run_id} step={step}: {sim_time} != {expected_time}")
        contiguous_times[step] = sim_time

    first_step_rows = by_step[1]
    if first_step_rows["cube"]["contact_state"] != "contact_persists":
        fail(f"cube step 1 contact state mismatch for {artifacts.run_id}")
    if first_step_rows["sphere"]["contact_state"] != "no_contact":
        fail(f"sphere step 1 contact state mismatch for {artifacts.run_id}")

    return {
        "steps": expected_steps,
        "rows": rows,
        "by_step": by_step,
        "contiguous_times": contiguous_times,
        "first_step_rows": first_step_rows,
    }


def recompute_body_energy(mass: float, position: tuple[float, float, float], linear_velocity: tuple[float, float, float]) -> tuple[float, float, float]:
    speed = vector_magnitude(linear_velocity)
    translational = 0.5 * mass * speed * speed
    potential = mass * 9.81 * max(0.0, float(position[2]))
    return translational, potential, translational + potential


def validate_runtime_vectors(run_id: str, trace: dict[str, Any]) -> dict[str, Any]:
    by_step = trace["by_step"]
    runtime_mismatches: list[dict[str, Any]] = []
    pose_mismatches: list[dict[str, Any]] = []
    sampled_mismatches: list[dict[str, Any]] = []
    sleeping_with_nonzero_sampled_velocity: list[dict[str, Any]] = []
    final_window_steps = list(range(EXPECTED_COMPLETED_STEPS - 29, EXPECTED_COMPLETED_STEPS + 1))
    final_window_summary: dict[str, Any] = {}

    for actor in BODY_SPECS:
        positions: list[tuple[float, float, float]] = []
        runtime_linear: list[tuple[float, float, float]] = []
        runtime_angular: list[tuple[float, float, float]] = []
        sampled_linear: list[tuple[float, float, float]] = []
        sampled_angular: list[tuple[float, float, float]] = []
        pose_linear: list[tuple[float, float, float]] = []
        runtime_speeds: list[float] = []
        runtime_planar_speeds: list[float] = []
        runtime_angular_speeds: list[float] = []
        sampled_speeds: list[float] = []
        sampled_planar_speeds: list[float] = []
        sampled_angular_speeds: list[float] = []
        pose_speeds: list[float] = []
        position_deltas: list[float] = []
        sleeping_values: list[int] = []

        previous_position = None
        for step in trace["steps"]:
            row = by_step[step][actor]
            position = (to_float(row[f"{actor}_px"]), to_float(row[f"{actor}_py"]), to_float(row[f"{actor}_pz"]))
            sampled = (
                to_float(row[f"{actor}_usd_sampled_vx"]),
                to_float(row[f"{actor}_usd_sampled_vy"]),
                to_float(row[f"{actor}_usd_sampled_vz"]),
            )
            runtime = (
                to_float(row[f"{actor}_runtime_vx"]),
                to_float(row[f"{actor}_runtime_vy"]),
                to_float(row[f"{actor}_runtime_vz"]),
            )
            runtime_ang = (
                to_float(row[f"{actor}_runtime_wx_rad_s"]),
                to_float(row[f"{actor}_runtime_wy_rad_s"]),
                to_float(row[f"{actor}_runtime_wz_rad_s"]),
            )
            sampled_ang = (
                to_float(row[f"{actor}_usd_sampled_wx_rad_s"]),
                to_float(row[f"{actor}_usd_sampled_wy_rad_s"]),
                to_float(row[f"{actor}_usd_sampled_wz_rad_s"]),
            )
            pose = (
                to_float(row[f"{actor}_pose_vx"]),
                to_float(row[f"{actor}_pose_vy"]),
                to_float(row[f"{actor}_pose_vz"]),
            )
            runtime_speed = to_float(row[f"{actor}_runtime_speed_mps"])
            runtime_planar = to_float(row[f"{actor}_runtime_planar_speed_mps"])
            runtime_vertical = to_float(row[f"{actor}_runtime_vertical_speed_mps"])
            runtime_angular_speed = to_float(row[f"{actor}_runtime_angular_speed_rad_s"])
            sampled_speed = to_float(row[f"{actor}_usd_sampled_speed_mps"])
            sampled_planar = to_float(row[f"{actor}_usd_sampled_planar_speed_mps"])
            sampled_angular_speed = to_float(row[f"{actor}_usd_sampled_angular_speed_rad_s"])
            pose_speed = to_float(row[f"{actor}_pose_speed_mps"])
            sleeping = parse_bool_field(row[f"{actor}_sleeping"], f"{actor}_sleeping", run_id, step, actor)

            positions.append(position)
            runtime_linear.append(runtime)
            runtime_angular.append(runtime_ang)
            sampled_linear.append(sampled)
            sampled_angular.append(sampled_ang)
            pose_linear.append(pose)
            runtime_speeds.append(runtime_speed)
            runtime_planar_speeds.append(runtime_planar)
            runtime_angular_speeds.append(runtime_angular_speed)
            sampled_speeds.append(sampled_speed)
            sampled_planar_speeds.append(sampled_planar)
            sampled_angular_speeds.append(sampled_angular_speed)
            pose_speeds.append(pose_speed)
            sleeping_values.append(sleeping)

            if abs(runtime_speed - vector_magnitude(runtime)) > TRACE_TOLERANCE:
                runtime_mismatches.append({"actor": actor, "step": step, "field": "runtime_speed_mps"})
            if abs(runtime_planar - math.sqrt(runtime[0] ** 2 + runtime[1] ** 2)) > TRACE_TOLERANCE:
                runtime_mismatches.append({"actor": actor, "step": step, "field": "runtime_planar_speed_mps"})
            if abs(runtime_vertical - runtime[2]) > TRACE_TOLERANCE:
                runtime_mismatches.append({"actor": actor, "step": step, "field": "runtime_vertical_speed_mps"})
            if abs(runtime_angular_speed - vector_magnitude(runtime_ang)) > TRACE_TOLERANCE:
                runtime_mismatches.append({"actor": actor, "step": step, "field": "runtime_angular_speed_rad_s"})
            if abs(to_float(row[f"{actor}_runtime_angular_speed_rad_s"]) - vector_magnitude(runtime_ang)) > TRACE_TOLERANCE:
                runtime_mismatches.append({"actor": actor, "step": step, "field": f"{actor}_runtime_angular_speed_rad_s"})

            if previous_position is None:
                expected_pose = (0.0, 0.0, 0.0)
            else:
                expected_pose = tuple((current - prior) / EXPECTED_DT for current, prior in zip(position, previous_position))
            if abs(to_float(row[f"{actor}_pose_vx"]) - expected_pose[0]) > TRACE_TOLERANCE or abs(to_float(row[f"{actor}_pose_vy"]) - expected_pose[1]) > TRACE_TOLERANCE or abs(to_float(row[f"{actor}_pose_vz"]) - expected_pose[2]) > TRACE_TOLERANCE:
                pose_mismatches.append({"actor": actor, "step": step, "field": "pose_linear_velocity"})
            if abs(pose_speed - vector_magnitude(expected_pose)) > TRACE_TOLERANCE:
                pose_mismatches.append({"actor": actor, "step": step, "field": "pose_speed_mps"})
            previous_position = position

            if abs(sampled_speed - vector_magnitude(sampled)) > TRACE_TOLERANCE:
                sampled_mismatches.append({"actor": actor, "step": step, "field": "usd_sampled_speed_mps"})
            if abs(sampled_planar - math.sqrt(sampled[0] ** 2 + sampled[1] ** 2)) > TRACE_TOLERANCE:
                sampled_mismatches.append({"actor": actor, "step": step, "field": "usd_sampled_planar_speed_mps"})
            if abs(sampled_angular_speed - vector_magnitude(sampled_ang)) > TRACE_TOLERANCE:
                sampled_mismatches.append({"actor": actor, "step": step, "field": "usd_sampled_angular_speed_rad_s"})

            if sleeping and sampled_speed > TRACE_TOLERANCE:
                sleeping_with_nonzero_sampled_velocity.append({"actor": actor, "step": step, "sampled_speed": sampled_speed})

        final_window_summary[actor] = {
            "position_m": {
                "min": [min(component[index] for component in positions[-30:]) for index in range(3)],
                "max": [max(component[index] for component in positions[-30:]) for index in range(3)],
                "speed": {
                    "min": min(vector_magnitude(position) for position in positions[-30:]),
                    "max": max(vector_magnitude(position) for position in positions[-30:]),
                },
            },
            "position_delta_m": {
                "min": min(position_deltas[-30:]) if position_deltas else 0.0,
                "max": max(position_deltas[-30:]) if position_deltas else 0.0,
            },
            "max_position_delta_m": max(position_deltas[-30:]) if position_deltas else 0.0,
            "runtime_linear_velocity_mps": {
                "min": [min(component[index] for component in runtime_linear[-30:]) for index in range(3)],
                "max": [max(component[index] for component in runtime_linear[-30:]) for index in range(3)],
                "speed": {"min": min(runtime_speeds[-30:]), "max": max(runtime_speeds[-30:])},
            },
            "runtime_speed_mps": {"min": min(runtime_speeds[-30:]), "max": max(runtime_speeds[-30:])},
            "runtime_planar_speed_mps": {"min": min(runtime_planar_speeds[-30:]), "max": max(runtime_planar_speeds[-30:])},
            "runtime_vertical_velocity_mps": {"min": min(component[2] for component in runtime_linear[-30:]), "max": max(component[2] for component in runtime_linear[-30:])},
            "runtime_angular_velocity_mps": {
                "min": [min(component[index] for component in runtime_angular[-30:]) for index in range(3)],
                "max": [max(component[index] for component in runtime_angular[-30:]) for index in range(3)],
            },
            "runtime_angular_speed_rad_s": {"min": min(runtime_angular_speeds[-30:]), "max": max(runtime_angular_speeds[-30:])},
            "usd_sampled_linear_velocity_mps": {
                "min": [min(component[index] for component in sampled_linear[-30:]) for index in range(3)],
                "max": [max(component[index] for component in sampled_linear[-30:]) for index in range(3)],
                "speed": {"min": min(sampled_speeds[-30:]), "max": max(sampled_speeds[-30:])},
            },
            "usd_sampled_speed_mps": {"min": min(sampled_speeds[-30:]), "max": max(sampled_speeds[-30:])},
            "usd_sampled_planar_speed_mps": {"min": min(sampled_planar_speeds[-30:]), "max": max(sampled_planar_speeds[-30:])},
            "usd_sampled_vertical_velocity_mps": {"min": min(component[2] for component in sampled_linear[-30:]), "max": max(component[2] for component in sampled_linear[-30:])},
            "usd_sampled_angular_velocity_rad_s": {
                "min": [min(component[index] for component in sampled_angular[-30:]) for index in range(3)],
                "max": [max(component[index] for component in sampled_angular[-30:]) for index in range(3)],
            },
            "usd_sampled_angular_speed_rad_s": {"min": min(sampled_angular_speeds[-30:]), "max": max(sampled_angular_speeds[-30:])},
            "pose_linear_velocity_mps": {
                "min": [min(component[index] for component in pose_linear[-30:]) for index in range(3)],
                "max": [max(component[index] for component in pose_linear[-30:]) for index in range(3)],
                "speed": {"min": min(pose_speeds[-30:]), "max": max(pose_speeds[-30:])},
            },
            "pose_speed_mps": {"min": min(pose_speeds[-30:]), "max": max(pose_speeds[-30:])},
            "pose_vertical_velocity_mps": {"min": min(component[2] for component in pose_linear[-30:]), "max": max(component[2] for component in pose_linear[-30:])},
            "sleeping": {"min": min(sleeping_values[-30:]), "max": max(sleeping_values[-30:])},
            "discrepancy_flags": {
                "runtime_vs_pose_velocity_mismatch": any(item["actor"] == actor for item in runtime_mismatches + pose_mismatches if item.get("field") in {"runtime_speed_mps", "runtime_planar_speed_mps", "runtime_vertical_speed_mps", "runtime_angular_speed_rad_s", "pose_linear_velocity", "pose_speed_mps"}),
                "sampled_vs_pose_velocity_mismatch": any(item["actor"] == actor for item in sampled_mismatches + pose_mismatches),
                "sampled_vs_runtime_velocity_mismatch": any(item["actor"] == actor for item in sampled_mismatches + runtime_mismatches),
                "sleeping_with_nonzero_sampled_velocity": any(item["actor"] == actor for item in sleeping_with_nonzero_sampled_velocity),
                "tolerance": RUNTIME_DIAGNOSTIC_TOLERANCE,
            },
        }

        # Recompute per-step position deltas after the main pass.
        for index, position in enumerate(positions):
            if index == 0:
                delta = 0.0
            else:
                delta = vector_magnitude(tuple(current - previous for current, previous in zip(position, positions[index - 1])))
            position_deltas.append(delta)

        # Replace position delta values with the complete list after it has been populated.
        final_window_summary[actor]["position_delta_m"] = {
            "min": min(position_deltas[-30:]),
            "max": max(position_deltas[-30:]),
        }
        final_window_summary[actor]["max_position_delta_m"] = max(position_deltas[-30:])
        final_window_summary[actor]["discrepancy_flags"] = {
            "runtime_vs_pose_velocity_mismatch": any(item["actor"] == actor for item in runtime_mismatches + pose_mismatches if item.get("field") in {"runtime_speed_mps", "runtime_planar_speed_mps", "runtime_vertical_speed_mps", "runtime_angular_speed_rad_s", "pose_linear_velocity", "pose_speed_mps"}),
            "sampled_vs_pose_velocity_mismatch": any(item["actor"] == actor for item in sampled_mismatches + pose_mismatches),
            "sampled_vs_runtime_velocity_mismatch": any(item["actor"] == actor for item in sampled_mismatches + runtime_mismatches),
            "sleeping_with_nonzero_sampled_velocity": any(item["actor"] == actor for item in sleeping_with_nonzero_sampled_velocity),
            "tolerance": RUNTIME_DIAGNOSTIC_TOLERANCE,
        }

    return {
        "runtime_mismatches": runtime_mismatches,
        "pose_mismatches": pose_mismatches,
        "sampled_mismatches": sampled_mismatches,
        "sleeping_with_nonzero_sampled_velocity": sleeping_with_nonzero_sampled_velocity,
        "final_window_steps": final_window_steps,
        "final_window_summary": final_window_summary,
    }


def validate_runtime_vectors_final(run_id: str, trace: dict[str, Any]) -> dict[str, Any]:
    by_step = trace["by_step"]
    final_window_steps = list(range(EXPECTED_COMPLETED_STEPS - 29, EXPECTED_COMPLETED_STEPS + 1))
    final_window_summary: dict[str, Any] = {}
    discrepancy_flags: dict[str, dict[str, Any]] = {}

    for actor in BODY_SPECS:
        sampled_linear: list[tuple[float, float, float]] = []
        runtime_linear: list[tuple[float, float, float]] = []
        pose_linear: list[tuple[float, float, float]] = []
        sampled_angular: list[tuple[float, float, float]] = []
        runtime_angular: list[tuple[float, float, float]] = []
        position_m: list[tuple[float, float, float]] = []
        position_delta: list[float] = []
        sampled_speed: list[float] = []
        runtime_speed: list[float] = []
        pose_speed: list[float] = []
        sampled_planar: list[float] = []
        runtime_planar: list[float] = []
        sampled_angular_speed: list[float] = []
        runtime_angular_speed: list[float] = []
        sleeping_values: list[int] = []

        for step in final_window_steps:
            row = by_step[step][actor]
            prev_row = by_step[step - 1][actor]
            pos = (to_float(row[f"{actor}_px"]), to_float(row[f"{actor}_py"]), to_float(row[f"{actor}_pz"]))
            prev_pos = (
                to_float(prev_row[f"{actor}_px"]),
                to_float(prev_row[f"{actor}_py"]),
                to_float(prev_row[f"{actor}_pz"]),
            )
            sampled = (
                to_float(row[f"{actor}_usd_sampled_vx"]),
                to_float(row[f"{actor}_usd_sampled_vy"]),
                to_float(row[f"{actor}_usd_sampled_vz"]),
            )
            runtime = (
                to_float(row[f"{actor}_runtime_vx"]),
                to_float(row[f"{actor}_runtime_vy"]),
                to_float(row[f"{actor}_runtime_vz"]),
            )
            pose = tuple((current - prior) / EXPECTED_DT for current, prior in zip(pos, prev_pos))
            sampled_ang = (
                to_float(row[f"{actor}_usd_sampled_wx_rad_s"]),
                to_float(row[f"{actor}_usd_sampled_wy_rad_s"]),
                to_float(row[f"{actor}_usd_sampled_wz_rad_s"]),
            )
            runtime_ang = (
                to_float(row[f"{actor}_runtime_wx_rad_s"]),
                to_float(row[f"{actor}_runtime_wy_rad_s"]),
                to_float(row[f"{actor}_runtime_wz_rad_s"]),
            )

            sampled_linear.append(sampled)
            runtime_linear.append(runtime)
            pose_linear.append(pose)
            sampled_angular.append(sampled_ang)
            runtime_angular.append(runtime_ang)
            position_m.append(pos)
            position_delta.append(vector_magnitude(tuple(current - prior for current, prior in zip(pos, prev_pos))))
            sampled_speed.append(to_float(row[f"{actor}_usd_sampled_speed_mps"]))
            runtime_speed.append(to_float(row[f"{actor}_runtime_speed_mps"]))
            pose_speed.append(vector_magnitude(pose))
            sampled_planar.append(vector_magnitude((sampled[0], sampled[1], 0.0)))
            runtime_planar.append(to_float(row[f"{actor}_runtime_planar_speed_mps"]))
            sampled_angular_speed.append(to_float(row[f"{actor}_usd_sampled_angular_speed_rad_s"]))
            runtime_angular_speed.append(to_float(row[f"{actor}_runtime_angular_speed_rad_s"]))
            sleeping_values.append(parse_bool_field(row[f"{actor}_sleeping"], f"{actor}_sleeping", run_id, step, actor))

        runtime_vs_pose = any(
            vector_magnitude(tuple(a - b for a, b in zip(runtime_linear[index], pose_linear[index]))) > RUNTIME_DIAGNOSTIC_TOLERANCE
            or abs(runtime_speed[index] - pose_speed[index]) > RUNTIME_DIAGNOSTIC_TOLERANCE
            for index in range(len(final_window_steps))
        )
        sampled_vs_pose = any(
            vector_magnitude(tuple(a - b for a, b in zip(sampled_linear[index], pose_linear[index]))) > RUNTIME_DIAGNOSTIC_TOLERANCE
            or abs(sampled_speed[index] - pose_speed[index]) > RUNTIME_DIAGNOSTIC_TOLERANCE
            for index in range(len(final_window_steps))
        )
        sampled_vs_runtime = any(
            vector_magnitude(tuple(a - b for a, b in zip(sampled_linear[index], runtime_linear[index]))) > RUNTIME_DIAGNOSTIC_TOLERANCE
            or abs(sampled_speed[index] - runtime_speed[index]) > RUNTIME_DIAGNOSTIC_TOLERANCE
            for index in range(len(final_window_steps))
        )
        sleeping_with_nonzero_sampled = any(
            sleeping_values[index] == 1 and sampled_speed[index] > RUNTIME_DIAGNOSTIC_TOLERANCE
            for index in range(len(final_window_steps))
        )

        final_window_summary[actor] = {
            "position_m": {
                "min": [min(component[index] for component in position_m) for index in range(3)],
                "max": [max(component[index] for component in position_m) for index in range(3)],
                "speed": {"min": min(vector_magnitude(value) for value in position_m), "max": max(vector_magnitude(value) for value in position_m)},
            },
            "position_delta_m": {"min": min(position_delta), "max": max(position_delta)},
            "max_position_delta_m": max(position_delta),
            "runtime_linear_velocity_mps": {
                "min": [min(component[index] for component in runtime_linear) for index in range(3)],
                "max": [max(component[index] for component in runtime_linear) for index in range(3)],
                "speed": {"min": min(runtime_speed), "max": max(runtime_speed)},
            },
            "runtime_total_speed_mps": {"min": min(runtime_speed), "max": max(runtime_speed)},
            "runtime_speed_mps": {"min": min(runtime_speed), "max": max(runtime_speed)},
            "runtime_planar_speed_mps": {"min": min(runtime_planar), "max": max(runtime_planar)},
            "runtime_vertical_velocity_mps": {"min": min(component[2] for component in runtime_linear), "max": max(component[2] for component in runtime_linear)},
            "runtime_angular_velocity_rad_s": {
                "min": [min(component[index] for component in runtime_angular) for index in range(3)],
                "max": [max(component[index] for component in runtime_angular) for index in range(3)],
            },
            "runtime_angular_speed_rad_s": {"min": min(runtime_angular_speed), "max": max(runtime_angular_speed)},
            "usd_sampled_linear_velocity_mps": {
                "min": [min(component[index] for component in sampled_linear) for index in range(3)],
                "max": [max(component[index] for component in sampled_linear) for index in range(3)],
                "speed": {"min": min(sampled_speed), "max": max(sampled_speed)},
            },
            "usd_sampled_speed_mps": {"min": min(sampled_speed), "max": max(sampled_speed)},
            "usd_sampled_planar_speed_mps": {"min": min(sampled_planar), "max": max(sampled_planar)},
            "usd_sampled_vertical_velocity_mps": {"min": min(component[2] for component in sampled_linear), "max": max(component[2] for component in sampled_linear)},
            "usd_sampled_angular_velocity_rad_s": {
                "min": [min(component[index] for component in sampled_angular) for index in range(3)],
                "max": [max(component[index] for component in sampled_angular) for index in range(3)],
            },
            "usd_sampled_angular_speed_rad_s": {"min": min(sampled_angular_speed), "max": max(sampled_angular_speed)},
            "pose_linear_velocity_mps": {
                "min": [min(component[index] for component in pose_linear) for index in range(3)],
                "max": [max(component[index] for component in pose_linear) for index in range(3)],
                "speed": {"min": min(pose_speed), "max": max(pose_speed)},
            },
            "pose_speed_mps": {"min": min(pose_speed), "max": max(pose_speed)},
            "pose_vertical_velocity_mps": {"min": min(component[2] for component in pose_linear), "max": max(component[2] for component in pose_linear)},
            "sleeping": {"min": min(sleeping_values), "max": max(sleeping_values)},
            "discrepancy_flags": {
                "runtime_vs_pose_velocity_mismatch": runtime_vs_pose,
                "sampled_vs_pose_velocity_mismatch": sampled_vs_pose,
                "sampled_vs_runtime_velocity_mismatch": sampled_vs_runtime,
                "sleeping_with_nonzero_sampled_velocity": sleeping_with_nonzero_sampled,
                "tolerance": RUNTIME_DIAGNOSTIC_TOLERANCE,
            },
        }

        discrepancy_flags[actor] = final_window_summary[actor]["discrepancy_flags"]

    return {
        "final_window_steps": final_window_steps,
        "final_window_summary": final_window_summary,
        "discrepancy_flags": discrepancy_flags,
    }


def validate_contact_and_rebound(artifacts: RunArtifacts, trace: dict[str, Any]) -> dict[str, Any]:
    summary = artifacts.summary
    contact_events = summary.get("contact_events", [])
    if not isinstance(contact_events, list) or not contact_events:
        fail(f"contact events missing for {artifacts.run_id}")

    counts_by_actor: dict[str, Counter[str]] = {"cube": Counter(), "sphere": Counter()}
    for event in contact_events:
        actor0 = event.get("actor0", "")
        actor = "cube" if "LowBounceCube" in actor0 else "sphere" if "HighBounceSphere" in actor0 else None
        if actor is None:
            fail(f"unexpected contact actor in {artifacts.run_id}: {actor0!r}")
        event_type = event.get("event_type")
        if event_type not in CONTACT_EVENT_TYPES:
            fail(f"unexpected contact event type in {artifacts.run_id}: {event_type!r}")
        counts_by_actor[actor][event_type] += 1

    summary_counts = summary.get("contact_counts", {})
    expected_counts = {
        "cube": dict(counts_by_actor["cube"]),
        "sphere": dict(counts_by_actor["sphere"]),
    }
    for actor in expected_counts:
        for label in ("contact_found", "contact_persists", "contact_lost", "contact_unknown"):
            expected_counts[actor].setdefault(label, 0)
    if summary_counts != expected_counts:
        fail(f"contact count mismatch for {artifacts.run_id}: {summary_counts!r} != {expected_counts!r}")

    cube_events = [event for event in contact_events if "LowBounceCube" in event.get("actor0", "")]
    sphere_events = [event for event in contact_events if "HighBounceSphere" in event.get("actor0", "")]
    cube_first_contact = next((int(event["step_index"]) for event in cube_events if event.get("event_type") == "contact_found"), None)
    sphere_first_contact = next((int(event["step_index"]) for event in sphere_events if event.get("event_type") == "contact_found"), None)
    sphere_rebound_step = int(summary.get("event_steps", {}).get("sphere_rebound_step", -1))
    cube_summary_first_contact = int(summary.get("event_steps", {}).get("cube_first_contact_step", -1))
    sphere_summary_first_contact = int(summary.get("event_steps", {}).get("sphere_first_contact_step", -1))
    if cube_first_contact != cube_summary_first_contact:
        fail(f"cube first contact step mismatch for {artifacts.run_id}: {cube_first_contact} != {cube_summary_first_contact}")
    if sphere_first_contact != sphere_summary_first_contact:
        fail(f"sphere first contact step mismatch for {artifacts.run_id}: {sphere_first_contact} != {sphere_summary_first_contact}")

    by_step = trace["by_step"]
    sphere_rows = [by_step[step]["sphere"] for step in trace["steps"]]
    sphere_rebound_detected_step = None
    sphere_contact_height = None
    previous_vertical = None
    first_contact_step = sphere_summary_first_contact
    for row in sphere_rows:
        step = int(row["step_index"])
        vertical = to_float(row["runtime_vertical_velocity_mps"])
        position_z = to_float(row["sphere_pz"])
        if step == first_contact_step:
            sphere_contact_height = position_z
        if (
            previous_vertical is not None
            and previous_vertical <= 0.0 < vertical
            and step >= first_contact_step
            and sphere_contact_height is not None
            and position_z > sphere_contact_height + 0.001
        ):
            sphere_rebound_detected_step = step
            break
        previous_vertical = vertical
    if sphere_rebound_detected_step != sphere_rebound_step:
        fail(
            f"sphere rebound step mismatch for {artifacts.run_id}: "
            f"{sphere_rebound_detected_step} != {sphere_rebound_step}"
        )

    max_post_contact_height = max(
        to_float(row["sphere_pz"])
        for row in sphere_rows
        if first_contact_step <= int(row["step_index"]) <= sphere_rebound_detected_step
    )
    reported_height = float(summary.get("event_steps", {}).get("sphere_rebound_height_m", float("nan")))
    recomputed_rebound_height = max_post_contact_height - float(sphere_contact_height or 0.0)
    if abs(recomputed_rebound_height - reported_height) > TOLERANCES["reboundHeightMeters"]:
        fail(f"rebound height mismatch for {artifacts.run_id}: {recomputed_rebound_height} != {reported_height}")

    return {
        "counts_by_actor": {actor: dict(counter) for actor, counter in counts_by_actor.items()},
        "contact_events": contact_events,
        "cube_first_contact_step": cube_first_contact,
        "sphere_first_contact_step": sphere_first_contact,
        "sphere_rebound_step": sphere_rebound_detected_step,
        "sphere_rebound_height_m": reported_height,
        "max_post_contact_height_m": max_post_contact_height,
        "unknown_event_count": counts_by_actor["cube"]["contact_unknown"] + counts_by_actor["sphere"]["contact_unknown"],
    }


def validate_sleep_state(artifacts: RunArtifacts, trace: dict[str, Any]) -> dict[str, Any]:
    by_step = trace["by_step"]
    sleeping_steps = {"cube": [], "sphere": []}
    wake_steps = {"cube": None, "sphere": None}
    first_sleep = {}
    for actor in BODY_SPECS:
        sleeping_seen = False
        for step in trace["steps"]:
            row = by_step[step][actor]
            sleeping = parse_bool_field(row[f"{actor}_sleeping"], f"{actor}_sleeping", artifacts.run_id, step, actor)
            if sleeping:
                sleeping_steps[actor].append(step)
                if not sleeping_seen:
                    first_sleep[actor] = step
                    sleeping_seen = True
            elif sleeping_seen and wake_steps[actor] is None:
                wake_steps[actor] = step
        if first_sleep.get(actor) is None:
            fail(f"{actor} never slept in {artifacts.run_id}")
        if wake_steps[actor] is not None:
            fail(f"{actor} woke after sleeping in {artifacts.run_id}: {wake_steps[actor]}")

    final_rows = {actor: by_step[EXPECTED_COMPLETED_STEPS][actor] for actor in BODY_SPECS}
    for actor, row in final_rows.items():
        if vector_magnitude((to_float(row[f"{actor}_runtime_vx"]), to_float(row[f"{actor}_runtime_vy"]), to_float(row[f"{actor}_runtime_vz"]))) > TRACE_TOLERANCE:
            fail(f"{actor} final runtime linear velocity not zero in {artifacts.run_id}")
        if vector_magnitude((to_float(row[f"{actor}_runtime_wx_rad_s"]), to_float(row[f"{actor}_runtime_wy_rad_s"]), to_float(row[f"{actor}_runtime_wz_rad_s"]))) > TRACE_TOLERANCE:
            fail(f"{actor} final runtime angular velocity not zero in {artifacts.run_id}")

    if first_sleep.get("cube") != int(artifacts.summary["event_steps"]["cube_first_sleep_step"]):
        fail(f"cube first sleep step mismatch in {artifacts.run_id}")
    if first_sleep.get("sphere") != int(artifacts.summary["event_steps"]["sphere_first_sleep_step"]):
        fail(f"sphere first sleep step mismatch in {artifacts.run_id}")

    return {
        "first_sleep_step": first_sleep,
        "wake_step": wake_steps,
        "sleeping_steps": sleeping_steps,
        "final_sleep_state": {actor: bool(int(final_rows[actor][f"{actor}_sleeping"])) for actor in BODY_SPECS},
    }


def validate_energy(artifacts: RunArtifacts, stage_masses: dict[str, float], trace: dict[str, Any]) -> dict[str, Any]:
    by_step = trace["by_step"]
    first_rows = {actor: by_step[1][actor] for actor in BODY_SPECS}
    final_rows = {actor: by_step[EXPECTED_COMPLETED_STEPS][actor] for actor in BODY_SPECS}
    initial_energy_summary = artifacts.summary.get("initial_energy", {})
    final_energy_summary = artifacts.summary.get("final_energy", {})

    energy_report: dict[str, Any] = {"initial": {}, "final": {}}
    for actor in BODY_SPECS:
        mass = stage_masses[actor]
        for phase, row, summary_block in (
            ("initial", first_rows[actor], initial_energy_summary.get(actor, {})),
            ("final", final_rows[actor], final_energy_summary.get(actor, {})),
        ):
            position = (
                to_float(row[f"{actor}_px"]),
                to_float(row[f"{actor}_py"]),
                to_float(row[f"{actor}_pz"]),
            )
            runtime_velocity = (
                to_float(row[f"{actor}_runtime_vx"]),
                to_float(row[f"{actor}_runtime_vy"]),
                to_float(row[f"{actor}_runtime_vz"]),
            )
            translational, potential, total = recompute_body_energy(mass, position, runtime_velocity)
            if abs(translational - to_float(row["runtime_kinetic_energy_j"])) > ENERGY_TOLERANCE:
                fail(f"{actor} runtime kinetic energy mismatch in {artifacts.run_id} ({phase})")
            if abs(potential - to_float(row["runtime_potential_energy_j"])) > ENERGY_TOLERANCE:
                fail(f"{actor} runtime potential energy mismatch in {artifacts.run_id} ({phase})")
            if abs(total - to_float(row["runtime_total_mechanical_energy_j"])) > ENERGY_TOLERANCE:
                fail(f"{actor} runtime total mechanical energy mismatch in {artifacts.run_id} ({phase})")
            if summary_block:
                if abs(translational - to_float(summary_block.get("runtime", {}).get("kinetic_energy_j"))) > ENERGY_TOLERANCE:
                    fail(f"{actor} summary runtime kinetic energy mismatch in {artifacts.run_id} ({phase})")
                if abs(potential - to_float(summary_block.get("runtime", {}).get("potential_energy_j"))) > ENERGY_TOLERANCE:
                    fail(f"{actor} summary runtime potential energy mismatch in {artifacts.run_id} ({phase})")
                if abs(total - to_float(summary_block.get("runtime", {}).get("total_mechanical_energy_j"))) > ENERGY_TOLERANCE:
                    fail(f"{actor} summary runtime total energy mismatch in {artifacts.run_id} ({phase})")
                if abs(translational - to_float(summary_block.get("kinetic_energy_j"))) > ENERGY_TOLERANCE:
                    fail(f"{actor} summary kinetic energy mismatch in {artifacts.run_id} ({phase})")
                if abs(potential - to_float(summary_block.get("potential_energy_j"))) > ENERGY_TOLERANCE:
                    fail(f"{actor} summary potential energy mismatch in {artifacts.run_id} ({phase})")
                if abs(total - to_float(summary_block.get("total_mechanical_energy_j"))) > ENERGY_TOLERANCE:
                    fail(f"{actor} summary total energy mismatch in {artifacts.run_id} ({phase})")
            energy_report[phase][actor] = {
                "mass": mass,
                "position_m": position,
                "runtime_velocity_mps": runtime_velocity,
                "kinetic_energy_j": translational,
                "potential_energy_j": potential,
                "total_mechanical_energy_j": total,
            }

    for actor in BODY_SPECS:
        if not energy_report["final"][actor]["total_mechanical_energy_j"] < energy_report["initial"][actor]["total_mechanical_energy_j"]:
            fail(f"{actor} mechanical energy did not decrease in {artifacts.run_id}")

    return energy_report


def validate_settling(artifacts: RunArtifacts, trace: dict[str, Any]) -> dict[str, Any]:
    by_step = trace["by_step"]
    cube_counter = 0
    sphere_counter = 0
    cube_settle_step = None
    sphere_settle_step = None
    run_settle_step = None
    sphere_rebounded = False
    first_rebound_step = artifacts.summary["event_steps"]["sphere_rebound_step"]
    final_steps = {"cube": None, "sphere": None}
    max_counter = {"cube": 0, "sphere": 0}

    for step in trace["steps"]:
        cube_row = by_step[step]["cube"]
        sphere_row = by_step[step]["sphere"]
        cube_ok = to_float(cube_row["runtime_planar_speed_mps"]) < 0.02 and to_float(cube_row["runtime_angular_speed_rad_s"]) < 0.05
        if cube_ok:
            cube_counter += 1
        else:
            cube_counter = 0
        if cube_counter > max_counter["cube"]:
            max_counter["cube"] = cube_counter
        if cube_settle_step is None and cube_counter >= SIMULATION_SETTINGS["settleWindow"]:
            cube_settle_step = step

        sphere_vertical = to_float(sphere_row["runtime_vertical_velocity_mps"])
        if step >= first_rebound_step and sphere_vertical > 0.0:
            sphere_rebounded = True
        sphere_ok = sphere_rebounded and to_float(sphere_row["runtime_total_speed_mps"]) < 0.02
        if sphere_ok:
            sphere_counter += 1
        else:
            sphere_counter = 0
        if sphere_counter > max_counter["sphere"]:
            max_counter["sphere"] = sphere_counter
        if sphere_settle_step is None and sphere_counter >= SIMULATION_SETTINGS["settleWindow"]:
            sphere_settle_step = step

        if cube_settle_step is not None and sphere_settle_step is not None and run_settle_step is None:
            run_settle_step = max(cube_settle_step, sphere_settle_step)

        final_steps["cube"] = cube_counter
        final_steps["sphere"] = sphere_counter

    if cube_settle_step != int(artifacts.summary["event_steps"]["cube_settle_step"]):
        fail(f"cube settle step mismatch in {artifacts.run_id}: {cube_settle_step}")
    if sphere_settle_step != int(artifacts.summary["event_steps"]["sphere_settle_step"]):
        fail(f"sphere settle step mismatch in {artifacts.run_id}: {sphere_settle_step}")
    if run_settle_step != int(artifacts.summary["event_steps"]["run_settle_step"]):
        fail(f"run settle step mismatch in {artifacts.run_id}: {run_settle_step}")

    return {
        "cube_settle_step": cube_settle_step,
        "sphere_settle_step": sphere_settle_step,
        "run_settle_step": run_settle_step,
        "cube_settle_counter_final": final_steps["cube"],
        "sphere_settle_counter_final": final_steps["sphere"],
        "cube_settle_counter_max": max_counter["cube"],
        "sphere_settle_counter_max": max_counter["sphere"],
    }


def validate_event_steps(artifacts: RunArtifacts, contact: dict[str, Any], sleep: dict[str, Any], settling: dict[str, Any]) -> dict[str, Any]:
    event_steps = artifacts.summary.get("event_steps", {})
    expected_event_steps = {
        "cube_first_contact_step": contact["cube_first_contact_step"],
        "cube_first_sleep_step": sleep["first_sleep_step"]["cube"],
        "cube_settle_step": settling["cube_settle_step"],
        "cube_wake_step": None,
        "run_settle_step": settling["run_settle_step"],
        "sphere_first_contact_step": contact["sphere_first_contact_step"],
        "sphere_first_sleep_step": sleep["first_sleep_step"]["sphere"],
        "sphere_rebound_height_m": contact["sphere_rebound_height_m"],
        "sphere_rebound_step": contact["sphere_rebound_step"],
        "sphere_settle_step": settling["sphere_settle_step"],
        "sphere_wake_step": None,
    }
    if event_steps != expected_event_steps:
        fail(f"event_steps mismatch for {artifacts.run_id}: {event_steps!r} != {expected_event_steps!r}")
    return expected_event_steps


def compare_summary_to_trace(artifacts: RunArtifacts, trace: dict[str, Any], energy: dict[str, Any], sleep: dict[str, Any], settling: dict[str, Any], contact: dict[str, Any], final_window: dict[str, Any]) -> dict[str, Any]:
    by_step = trace["by_step"]
    final_rows = {actor: by_step[EXPECTED_COMPLETED_STEPS][actor] for actor in BODY_SPECS}
    final_state_summary = artifacts.summary.get("final_state", {})
    if set(final_state_summary) != set(BODY_SPECS):
        fail(f"final_state actor keys mismatch for {artifacts.run_id}")

    for actor in BODY_SPECS:
        summary_actor = final_state_summary[actor]
        final_row = final_rows[actor]
        runtime_position = [to_float(final_row[f"{actor}_px"]), to_float(final_row[f"{actor}_py" ]), to_float(final_row[f"{actor}_pz"])]
        runtime_velocity = [to_float(final_row[f"{actor}_runtime_vx"]), to_float(final_row[f"{actor}_runtime_vy"]), to_float(final_row[f"{actor}_runtime_vz"])]
        runtime_angular_velocity = [to_float(final_row[f"{actor}_runtime_wx_rad_s"]), to_float(final_row[f"{actor}_runtime_wy_rad_s"]), to_float(final_row[f"{actor}_runtime_wz_rad_s"])]
        if [round(v, 6) for v in runtime_position] != [round(v, 6) for v in summary_actor["runtime"]["position_m"]]:
            fail(f"{actor} final runtime position mismatch in {artifacts.run_id}")
        if [round(v, 6) for v in runtime_velocity] != [round(v, 6) for v in summary_actor["runtime"]["linear_velocity_mps"]]:
            fail(f"{actor} final runtime velocity mismatch in {artifacts.run_id}")
        if [round(v, 6) for v in runtime_angular_velocity] != [round(v, 6) for v in summary_actor["runtime"]["angular_velocity_rad_s"]]:
            fail(f"{actor} final runtime angular velocity mismatch in {artifacts.run_id}")
        if abs(to_float(final_row[f"{actor}_runtime_speed_mps"]) - summary_actor["runtime"]["speed_mps"]) > VELOCITY_TOLERANCE:
            fail(f"{actor} final runtime speed mismatch in {artifacts.run_id}")
        if abs(to_float(final_row[f"{actor}_runtime_angular_speed_rad_s"]) - summary_actor["runtime"]["angular_speed_rad_s"]) > VELOCITY_TOLERANCE:
            fail(f"{actor} final runtime angular speed mismatch in {artifacts.run_id}")
        if bool(int(final_row[f"{actor}_sleeping"])) != bool(summary_actor["sleeping"]):
            fail(f"{actor} final sleep state mismatch in {artifacts.run_id}")

    completion = artifacts.summary.get("completion", {})
    expected_completion = {
        "cube_contacted_ground": True,
        "cube_settled": True,
        "sphere_contacted_ground": True,
        "sphere_rebound_detected": True,
        "sphere_settled": True,
        "unmet_conditions": [],
    }
    if completion != expected_completion:
        fail(f"completion block mismatch for {artifacts.run_id}")

    return {
        "final_state": final_state_summary,
        "completion": completion,
        "sleep_state_summary": sleep,
        "settling_summary": settling,
        "contact_summary": contact,
        "final_30_step_ranges": final_window,
    }


def validate_final_window_ranges(artifacts: RunArtifacts, trace: dict[str, Any], runtime_checks: dict[str, Any]) -> dict[str, Any]:
    expected = artifacts.summary.get("final_30_step_ranges", {})
    actual = runtime_checks["final_window_summary"]

    def compare_scalar_range(label: str, expected_range: dict[str, Any], actual_range: dict[str, Any], tolerance: float = TRACE_TOLERANCE) -> None:
        for bound in ("min", "max"):
            if abs(float(expected_range[bound]) - float(actual_range[bound])) > tolerance:
                fail(f"{label} {bound} mismatch for {artifacts.run_id}: {expected_range[bound]!r} != {actual_range[bound]!r}")

    def compare_vector_range(label: str, expected_range: dict[str, Any], actual_range: dict[str, Any], tolerance: float = TRACE_TOLERANCE) -> None:
        compare_scalar_range(f"{label}.speed", expected_range["speed"], actual_range["speed"], tolerance)
        for bound in ("min", "max"):
            for index in range(3):
                if abs(float(expected_range[bound][index]) - float(actual_range[bound][index])) > tolerance:
                    fail(
                        f"{label} {bound}[{index}] mismatch for {artifacts.run_id}: "
                        f"{expected_range[bound][index]!r} != {actual_range[bound][index]!r}"
                    )

    for actor in BODY_SPECS:
        expected_actor = expected.get(actor, {})
        actual_actor = actual.get(actor, {})
        if not expected_actor:
            fail(f"missing final 30-step summary for {actor} in {artifacts.run_id}")
        for key in (
            "position_m",
            "runtime_linear_velocity_mps",
            "max_position_delta_m",
            "runtime_speed_mps",
            "runtime_angular_speed_rad_s",
            "usd_sampled_linear_velocity_mps",
            "usd_sampled_speed_mps",
            "usd_sampled_angular_speed_rad_s",
            "pose_linear_velocity_mps",
            "pose_speed_mps",
            "sleeping",
        ):
            if key not in expected_actor or key not in actual_actor:
                fail(f"missing final window metric {key} for {actor} in {artifacts.run_id}")
        compare_vector_range(f"{actor}.position_m", expected_actor["position_m"], actual_actor["position_m"])
        compare_vector_range(f"{actor}.runtime_linear_velocity_mps", expected_actor["runtime_linear_velocity_mps"], actual_actor["runtime_linear_velocity_mps"])
        compare_vector_range(f"{actor}.usd_sampled_linear_velocity_mps", expected_actor["usd_sampled_linear_velocity_mps"], actual_actor["usd_sampled_linear_velocity_mps"])
        compare_vector_range(f"{actor}.pose_linear_velocity_mps", expected_actor["pose_linear_velocity_mps"], actual_actor["pose_linear_velocity_mps"])
        compare_scalar_range(f"{actor}.max_position_delta_m", {"min": expected_actor["max_position_delta_m"], "max": expected_actor["max_position_delta_m"]}, {"min": actual_actor["max_position_delta_m"], "max": actual_actor["max_position_delta_m"]})
        compare_scalar_range(f"{actor}.runtime_speed_mps", expected_actor["runtime_speed_mps"], actual_actor["runtime_speed_mps"])
        compare_scalar_range(f"{actor}.runtime_angular_speed_rad_s", expected_actor["runtime_angular_speed_rad_s"], actual_actor["runtime_angular_speed_rad_s"])
        compare_scalar_range(f"{actor}.usd_sampled_speed_mps", expected_actor["usd_sampled_speed_mps"], actual_actor["usd_sampled_speed_mps"])
        compare_scalar_range(f"{actor}.usd_sampled_angular_speed_rad_s", expected_actor["usd_sampled_angular_speed_rad_s"], actual_actor["usd_sampled_angular_speed_rad_s"])
        compare_scalar_range(f"{actor}.pose_speed_mps", expected_actor["pose_speed_mps"], actual_actor["pose_speed_mps"])
        if expected_actor["sleeping"] != actual_actor["sleeping"]:
            fail(f"sleeping range mismatch for {actor} in {artifacts.run_id}")
    return expected


def validate_result_artifacts(stage_data: dict[str, Any], run_results: dict[str, RunArtifacts]) -> dict[str, Any]:
    stage_lines = stage_data["run-01"]["usda_stage"]["hierarchy_lines"]
    expected_lines = stage_data["run-01"]["usda_stage"]["expected_hierarchy_lines"]
    if stage_lines != expected_lines:
        fail("canonical hierarchy does not match expected-hierarchy.txt")
    if stage_data["run-01"]["usda_stage"]["hierarchy_lines"] != stage_data["run-02"]["usda_stage"]["hierarchy_lines"]:
        fail("run-01 and run-02 stage hierarchies differ")
    if stage_data["run-01"]["usda_hash"] != stage_data["run-02"]["usda_hash"]:
        fail("run-01 and run-02 USDA hashes differ")
    if stage_data["run-01"]["usd_hash"] != stage_data["run-02"]["usd_hash"]:
        fail("run-01 and run-02 stage hashes differ")
    if stage_data["run-01"]["usda_hash"] != EXPECTED_STAGE_HASHES["usda"]:
        fail("canonical USDA hash does not match expected value")
    if stage_data["run-01"]["usd_hash"] != EXPECTED_STAGE_HASHES["usd"]:
        fail("canonical stage hashes do not match expected values")

    return {
        "stage_identical": True,
        "stage_hashes": {"usda": stage_data["run-01"]["usda_hash"], "usd": stage_data["run-01"]["usd_hash"]},
        "expected_stage_hashes": EXPECTED_STAGE_HASHES,
    }


def stage_mass_lookup(stage: Usd.Stage) -> dict[str, float]:
    masses: dict[str, float] = {}
    for actor, spec in BODY_SPECS.items():
        prim = stage.GetPrimAtPath(spec["path"])
        masses[actor] = float(UsdPhysics.MassAPI(prim).GetMassAttr().Get())
    return masses


def load_stage(path: Path) -> Usd.Stage:
    stage = Usd.Stage.Open(str(path))
    if not stage:
        fail(f"failed to open stage: {path}")
    return stage


def inspect_all() -> dict[str, Any]:
    report: dict[str, Any] = {
        "status": "failed",
        "failure_reason": None,
        "inspection": {
            "image_ref": EXPECTED_IMAGE_REF,
            "steps_per_second": SIMULATION_SETTINGS["stepsPerSecond"],
            "max_steps": SIMULATION_SETTINGS["maxSteps"],
            "settle_window": SIMULATION_SETTINGS["settleWindow"],
            "tolerances": dict(TOLERANCES),
        },
        "stage": {},
        "runs": {},
        "warnings": [],
    }

    stage_data: dict[str, Any] = {}
    for run_id in RUN_IDS:
        artifacts = load_run_artifacts(run_id)
        stage_path_info = {
            "usda": artifacts.stage_paths["usda"],
            "usd": artifacts.stage_paths["usd"],
        }
        validate_header(stage_path_info["usda"], b"#usda", f"{run_id} USDA")
        validate_header(stage_path_info["usd"], b"PXR-USDC", f"{run_id} USD")
        stage_usda = load_stage(stage_path_info["usda"])
        stage_usd = load_stage(stage_path_info["usd"])
        stage_data[run_id] = {
            "usda_path": str(stage_path_info["usda"]),
            "usd_path": str(stage_path_info["usd"]),
            "usda_size": stage_path_info["usda"].stat().st_size,
            "usd_size": stage_path_info["usd"].stat().st_size,
            "usda_hash": sha256_file(stage_path_info["usda"]),
            "usd_hash": sha256_file(stage_path_info["usd"]),
            "usda_stage": validate_stage_metadata(stage_usda, run_id),
            "usd_stage": validate_stage_metadata(stage_usd, run_id),
        }

    stage_masses = stage_mass_lookup(load_stage(RUN_OUTPUT_DIRS["run-01"] / "physics_scene.usda"))
    stage_integrity = validate_result_artifacts(stage_data, {run_id: load_run_artifacts(run_id) for run_id in RUN_IDS})

    for run_id in RUN_IDS:
        artifacts = load_run_artifacts(run_id)
        summary_file = validate_file_inventory(artifacts)
        trace = validate_trace_continuity(artifacts)
        runtime_checks = validate_runtime_vectors_final(run_id, trace)
        contact = validate_contact_and_rebound(artifacts, trace)
        sleep = validate_sleep_state(artifacts, trace)
        energy = validate_energy(artifacts, stage_masses, trace)
        settling = validate_settling(artifacts, trace)
        events = validate_event_steps(artifacts, contact, sleep, settling)
        compare = compare_summary_to_trace(artifacts, trace, energy, sleep, settling, contact, runtime_checks["final_window_summary"])
        final_window = validate_final_window_ranges(artifacts, trace, runtime_checks)

        report["runs"][run_id] = {
            "paths": {
                "summary": f"results/{run_id}/summary.json",
                "trace": f"results/{run_id}/step_metrics.csv",
                "usda": f"output/{run_id}/physics_scene.usda",
                "usd": f"output/{run_id}/physics_scene.usd",
            },
            "sizes": summary_file["sizes"],
            "hashes": summary_file["hashes"],
            "artifact_hashes": summary_file["artifact_hashes"],
            "summary_file": artifacts.summary,
            "trace": {
                "rows": len(artifacts.rows),
                "steps": len(trace["steps"]),
                "time_continuity": {
                    "dt": EXPECTED_DT,
                    "first_step": 1,
                    "final_step": EXPECTED_COMPLETED_STEPS,
                    "final_duration_s": round(EXPECTED_COMPLETED_STEPS * EXPECTED_DT, 6),
                },
                "contact_state_at_step_1": {
                    "cube": trace["first_step_rows"]["cube"]["contact_state"],
                    "sphere": trace["first_step_rows"]["sphere"]["contact_state"],
                },
            },
            "contact": contact,
            "sleep": sleep,
            "energy": energy,
            "settling": settling,
            "events": events,
            "summary_to_trace": compare,
            "final_30_step_ranges": final_window,
            "runtime_diagnostics": {
                "final_window_steps": runtime_checks["final_window_steps"],
                "discrepancy_flags": runtime_checks["discrepancy_flags"],
            },
        }

    report["stage"] = stage_data
    report["stage_integrity"] = stage_integrity
    report["status"] = "passed"
    return report


def write_summary_report(report: dict[str, Any]) -> Path:
    path = RESULTS_DIR / "summary.md"
    path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = ["# Phase 6 Inspection Report", ""]
    lines.append(f"Status: {report['status'].upper()}")
    if report.get("failure_reason"):
        lines.append(f"Failure reason: {report['failure_reason']}")
    lines.append("")
    lines.append("## Inspection Contract")
    lines.extend(
        [
            f"- Isaac Sim image: `{report['inspection']['image_ref']}`",
            f"- Fixed timestep: `{report['inspection']['steps_per_second']} Hz`",
            f"- Max steps: `{report['inspection']['max_steps']}`",
            f"- Settling window: `{report['inspection']['settle_window']}` steps",
        ]
    )
    lines.append("")
    lines.append("## Canonical Stage Integrity")
    lines.append(f"- run-01 USDA SHA256: `{report['stage']['run-01']['usda_hash']}`")
    lines.append(f"- run-01 USD SHA256: `{report['stage']['run-01']['usd_hash']}`")
    lines.append(f"- run-02 USDA SHA256: `{report['stage']['run-02']['usda_hash']}`")
    lines.append(f"- run-02 USD SHA256: `{report['stage']['run-02']['usd_hash']}`")
    lines.append(f"- Stages byte-identical across run-01 and run-02: `{report['stage_integrity']['stage_identical']}`")
    lines.append("")
    lines.append("## Artifact Inventory")
    lines.extend(md_table(
        ["Run", "File", "Bytes", "SHA256"],
        [
            ["run-01", "results/run-01/summary.json", str(report["runs"]["run-01"]["sizes"]["summary"]), report["runs"]["run-01"]["hashes"]["summary"]],
            ["run-01", "results/run-01/step_metrics.csv", str(report["runs"]["run-01"]["sizes"]["trace"]), report["runs"]["run-01"]["hashes"]["trace"]],
            ["run-01", "output/run-01/physics_scene.usda", str(report["runs"]["run-01"]["sizes"]["usda"]), report["runs"]["run-01"]["hashes"]["usda"]],
            ["run-01", "output/run-01/physics_scene.usd", str(report["runs"]["run-01"]["sizes"]["usd"]), report["runs"]["run-01"]["hashes"]["usd"]],
            ["run-02", "results/run-02/summary.json", str(report["runs"]["run-02"]["sizes"]["summary"]), report["runs"]["run-02"]["hashes"]["summary"]],
            ["run-02", "results/run-02/step_metrics.csv", str(report["runs"]["run-02"]["sizes"]["trace"]), report["runs"]["run-02"]["hashes"]["trace"]],
            ["run-02", "output/run-02/physics_scene.usda", str(report["runs"]["run-02"]["sizes"]["usda"]), report["runs"]["run-02"]["hashes"]["usda"]],
            ["run-02", "output/run-02/physics_scene.usd", str(report["runs"]["run-02"]["sizes"]["usd"]), report["runs"]["run-02"]["hashes"]["usd"]],
            ["report", "results/summary.md", "pending", "pending"],
        ],
    ))
    lines.append("")
    lines.append("## Trace Validation")
    for run_id in RUN_IDS:
        run = report["runs"][run_id]
        lines.append(f"### {run_id}")
        lines.append(f"- CSV rows: `{run['trace']['rows']}`")
        lines.append(f"- Completed steps: `{run['trace']['steps']}`")
        lines.append(f"- Fixed timestep: `{format_float(run['trace']['time_continuity']['dt'], 6)}` s")
        lines.append(f"- Final duration: `{format_float(run['trace']['time_continuity']['final_duration_s'], 6)}` s")
        lines.append(f"- Step 1 contact state: cube=`{run['trace']['contact_state_at_step_1']['cube']}`, sphere=`{run['trace']['contact_state_at_step_1']['sphere']}`")
        lines.append(f"- Cube settle step: `{run['settling']['cube_settle_step']}`")
        lines.append(f"- Sphere settle step: `{run['settling']['sphere_settle_step']}`")
        lines.append(f"- Run settle step: `{run['settling']['run_settle_step']}`")
        lines.append(f"- Cube first sleep step: `{run['sleep']['first_sleep_step']['cube']}`")
        lines.append(f"- Sphere first sleep step: `{run['sleep']['first_sleep_step']['sphere']}`")
        lines.append(f"- Final sleep state: cube=`{run['sleep']['final_sleep_state']['cube']}`, sphere=`{run['sleep']['final_sleep_state']['sphere']}`")
        lines.append(f"- First contact step: cube=`{run['contact']['cube_first_contact_step']}`, sphere=`{run['contact']['sphere_first_contact_step']}`")
        lines.append(f"- Sphere rebound step: `{run['contact']['sphere_rebound_step']}`")
        lines.append(f"- Maximum post-contact sphere height: `{format_float(run['contact']['max_post_contact_height_m'], 6)}` m")
        lines.append(f"- Contact counts: cube={run['contact']['counts_by_actor']['cube']}, sphere={run['contact']['counts_by_actor']['sphere']}")
        lines.append("")
    lines.append("## State-Source Policy")
    lines.append("- PhysX runtime state drives settlement, rebound qualification, and energy acceptance.")
    lines.append("- Authored USD rigid-body velocities are diagnostic only and may become stale after sleep.")
    lines.append(f"- Declared sources: {json.dumps(EXPECTED_STATE_SOURCES, indent=2, sort_keys=True)}")
    lines.append("")
    lines.append("## Energy Findings")
    for run_id in RUN_IDS:
        run = report["runs"][run_id]
        lines.append(f"### {run_id}")
        for actor in BODY_SPECS:
            initial = run["energy"]["initial"][actor]
            final = run["energy"]["final"][actor]
            lines.append(
                f"- {actor}: initial total `{format_float(initial['total_mechanical_energy_j'], 6)}` J, final total `{format_float(final['total_mechanical_energy_j'], 6)}` J"
            )
            lines.append(
                f"  - translational KE: initial `{format_float(initial['kinetic_energy_j'], 6)}` J, final `{format_float(final['kinetic_energy_j'], 6)}` J"
            )
            lines.append(
                f"  - potential energy: initial `{format_float(initial['potential_energy_j'], 6)}` J, final `{format_float(final['potential_energy_j'], 6)}` J"
            )
    lines.append("")
    lines.append("## Contact Classification")
    lines.append("- `contact_found`, `contact_lost`, and `contact_unknown` are the only event labels present in the persisted callback stream.")
    lines.append("- `contact_persists` appears only as a zero bucket in the summary contact counts and does not appear as a persisted event label.")
    lines.append("- contact_unknown records are repeated callback payloads that the runner could not map to found/persists/lost transitions.")
    lines.append("")
    lines.append("## Final-Window Diagnostics")
    for run_id in RUN_IDS:
        run = report["runs"][run_id]
        lines.append(f"### {run_id}")
        lines.append(f"- Runtime/pose/sample mismatch flags: {json.dumps(run['runtime_diagnostics'], indent=2, sort_keys=True)}")
        lines.append(f"- Final 30-step ranges: {json.dumps(run['final_30_step_ranges'], indent=2, sort_keys=True)}")
    lines.append("")
    lines.append("## Warnings and Evidence Limits")
    lines.append("- Step 0 contact evidence exists only in the summary contact event stream; the CSV trace starts at the first completed advancement step.")
    lines.append("- Authored USD velocity values remain as diagnostics even when the bodies are sleeping.")
    lines.append("- The inspection cross-checks the summary and trace rather than trusting the summary status field alone.")

    with path.open("w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return path


def main() -> int:
    report: dict[str, Any] | None = None
    exit_code = 0
    try:
        report = inspect_all()
        report_path = write_summary_report(report)
        report["stage"]["report_hash"] = sha256_file(report_path)
        report["stage"]["report_size"] = report_path.stat().st_size
        verify_success_gate(report, report_path)
        print("PHYSICS_INSPECT: root stage opened", flush=True)
        print("PHYSICS_INSPECT: run results opened", flush=True)
        print("PHYSICS_INSPECT: world metadata validated", flush=True)
        print("PHYSICS_INSPECT: hierarchy validated", flush=True)
        print("PHYSICS_INSPECT: inspection passed", flush=True)
        print(f"PHYSICS_INSPECT: summary report written to {report_path}", flush=True)
        print("PHYSICS_INSPECT: formal inspection completed successfully", flush=True)
        print("PHYSICS_INSPECT: skipping SimulationApp.close() due to reproduced Isaac Sim 6.0.1 busy TaskGroup teardown defect", flush=True)
        print("PHYSICS_INSPECT: terminating one-shot inspector", flush=True)
        flush_output_streams()
        os._exit(0)
    except Exception as exc:
        exit_code = 1
        if report is None:
            report = {
                "status": "failed",
                "failure_reason": str(exc),
                "inspection": {"image_ref": EXPECTED_IMAGE_REF},
                "runs": {},
                "stage": {},
                "warnings": [],
            }
        else:
            report["status"] = "failed"
            report["failure_reason"] = str(exc)
        try:
            write_summary_report(report)
        except Exception:
            pass
        traceback.print_exc()
        flush_output_streams()

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
