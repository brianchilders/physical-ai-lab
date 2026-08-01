from __future__ import annotations

import argparse
import csv
import json
from math import sqrt
from pathlib import Path
from typing import Any

from physics_common import RESULTS_DIR, TOLERANCES, read_json, round_vector, sha256_file, write_json


TRACE_REQUIRED_COLUMNS = (
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
)

TRACE_STRING_FIELDS = {
    "run_id",
    "actor",
    "contact_state",
    "rebound_state",
}

TRACE_INTEGER_FIELDS = {
    "step_index",
    "settle_counter",
}

TRACE_BOOLEAN_FIELDS = {
    "sleeping",
    "contact_found",
    "contact_persists",
    "contact_lost",
    "contact_active",
    "cube_sleeping",
    "cube_contact_found",
    "cube_contact_persists",
    "cube_contact_lost",
    "sphere_sleeping",
    "sphere_contact_found",
    "sphere_contact_persists",
    "sphere_contact_lost",
    "sphere_rebounded",
    "run_settled",
}

TRACE_TOLERANCES = {
    "positionMeters": 0.001,
    "velocityMetersPerSecond": 0.001,
    "orientationQuat": 0.000001,
    "angularVelocityRadPerSec": 0.001,
    "angularSpeedRadPerSec": 0.001,
    "simulationTimeSeconds": 0.000001,
    "energyJoules": 0.02,
    "stepCount": 1,
}

EXPECTED_METADATA_DIFFS = {
    ("run_id",),
    ("stage", "run_output_dir"),
    ("stage", "run_results_dir"),
    ("stage", "snapshot_usd"),
    ("stage", "snapshot_usda"),
    ("artifact_hashes", "trace_csv"),
    ("image_ref",),
}

PHYSICS_SUMMARY_PATHS = {
    ("completion",),
    ("contact_counts",),
    ("contact_events",),
    ("cross_source_discrepancy_flags",),
    ("event_steps",),
    ("failure_reason",),
    ("final_30_step_ranges",),
    ("final_energy",),
    ("final_state",),
    ("initial_energy",),
    ("pass_fail",),
    ("physics_simulation_view_source",),
    ("schema_version",),
    ("settle_counters",),
    ("settlement_velocity_source",),
    ("simulation",),
    ("sleep_state_source",),
    ("stage", "canonical_usd"),
    ("stage", "canonical_usda"),
    ("state_sources",),
    ("status",),
    ("thresholds",),
    ("world",),
    ("authoritative_runtime_pose_source",),
    ("authoritative_runtime_velocity_source",),
    ("angular_speed_formula",),
}


def fail(message: str) -> None:
    print(f"PHYSICS_COMPARE: FAIL: {message}", flush=True)
    raise SystemExit(1)


def load_trace(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def to_float(value: str | None) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


def compare_scalar(value_a: float, value_b: float, tolerance: float) -> bool:
    return abs(value_a - value_b) <= tolerance


def compare_vector(values_a: list[float], values_b: list[float], tolerance: float) -> bool:
    return sqrt(sum((a - b) ** 2 for a, b in zip(values_a, values_b))) <= tolerance


def compare_path(path: tuple[str, ...], value_a: Any, value_b: Any) -> dict[str, Any]:
    return {
        "path": ".".join(path),
        "run_a_value": value_a,
        "run_b_value": value_b,
    }


def required_columns_missing(fieldnames: list[str]) -> list[str]:
    present = set(fieldnames)
    return [column for column in TRACE_REQUIRED_COLUMNS if column not in present]


def field_tolerance(field: str) -> float | None:
    if field in TRACE_STRING_FIELDS:
        return None
    if field in TRACE_INTEGER_FIELDS:
        return float(TRACE_TOLERANCES["stepCount"])
    if field in TRACE_BOOLEAN_FIELDS:
        return 0.0
    if field == "sim_time_s":
        return TRACE_TOLERANCES["simulationTimeSeconds"]
    if field.startswith("position_") or field.endswith("_px") or field.endswith("_py") or field.endswith("_pz"):
        return TRACE_TOLERANCES["positionMeters"]
    if field.startswith("orientation_") or field.endswith("_orientation_x") or field.endswith("_orientation_y") or field.endswith("_orientation_z") or field.endswith("_orientation_w"):
        return TRACE_TOLERANCES["orientationQuat"]
    if "angular_velocity" in field or field.endswith("_wx_rad_s") or field.endswith("_wy_rad_s") or field.endswith("_wz_rad_s"):
        return TRACE_TOLERANCES["angularVelocityRadPerSec"]
    if "angular_speed" in field:
        return TRACE_TOLERANCES["angularSpeedRadPerSec"]
    if "linear_velocity" in field or field.endswith("_vx") or field.endswith("_vy") or field.endswith("_vz") or field.endswith("_speed_mps") or field.endswith("vertical_velocity_mps") or field.endswith("planar_speed_mps") or field.endswith("speed_mps"):
        return TRACE_TOLERANCES["velocityMetersPerSecond"]
    if field.endswith("_energy_j"):
        return TRACE_TOLERANCES["energyJoules"]
    if field.endswith("_settled"):
        return 0.0
    return 0.0


def normalise_value(field: str, value: str | None) -> Any:
    if field in TRACE_STRING_FIELDS:
        return "" if value is None else value
    if field in TRACE_INTEGER_FIELDS or field in TRACE_BOOLEAN_FIELDS:
        return int(float(value or 0.0))
    return to_float(value)


def field_role(field: str) -> str:
    if field.startswith("usd_sampled_") or "_usd_sampled_" in field:
        return "diagnostic"
    if field in TRACE_STRING_FIELDS or field in TRACE_BOOLEAN_FIELDS or field in TRACE_INTEGER_FIELDS:
        return "state"
    return "authoritative"


def compare_rows(rows_a: list[dict[str, str]], rows_b: list[dict[str, str]], fieldnames: list[str]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    indexed_a = {(int(row["step_index"]), row["actor"]): row for row in rows_a}
    indexed_b = {(int(row["step_index"]), row["actor"]): row for row in rows_b}
    keys_a = set(indexed_a)
    keys_b = set(indexed_b)

    if keys_a != keys_b:
        missing_a = sorted(keys_b - keys_a)
        missing_b = sorted(keys_a - keys_b)
        fail(f"trace step/actor coverage mismatch: missing from run-a={missing_a}, missing from run-b={missing_b}")

    ordered_keys = sorted(keys_a)
    compare_fields = [field for field in fieldnames if field not in {"run_id"}]
    field_stats: dict[str, dict[str, Any]] = {}
    comparison_rows: list[dict[str, Any]] = []
    first_divergence: dict[str, Any] | None = None

    for field in compare_fields:
        tolerance = field_tolerance(field)
        if tolerance is None:
            continue

        max_abs_diff = 0.0
        outside_tolerance = 0
        violating_indices: list[int] = []

        for row_index, key in enumerate(ordered_keys):
            row_a = indexed_a[key]
            row_b = indexed_b[key]
            value_a = normalise_value(field, row_a.get(field))
            value_b = normalise_value(field, row_b.get(field))
            diff = abs(value_a - value_b)
            max_abs_diff = max(max_abs_diff, diff)
            if diff > tolerance:
                outside_tolerance += 1
                violating_indices.append(row_index)
                if first_divergence is None:
                    first_divergence = {
                        "row_index": row_index,
                        "step_index": key[0],
                        "actor": key[1],
                        "field": field,
                        "run_a_value": value_a,
                        "run_b_value": value_b,
                        "delta": value_a - value_b,
                        "tolerance": tolerance,
                    }

        if outside_tolerance == 0:
            divergence_mode = "exact"
        else:
            first_violation = violating_indices[0]
            persistent = violating_indices == list(range(first_violation, len(ordered_keys)))
            divergence_mode = "persistent" if persistent else "transient"

        field_stats[field] = {
            "role": field_role(field),
            "tolerance": tolerance,
            "max_abs_diff": max_abs_diff,
            "outside_tolerance_count": outside_tolerance,
            "first_divergence_row_index": violating_indices[0] if violating_indices else None,
            "first_divergence_step_index": ordered_keys[violating_indices[0]][0] if violating_indices else None,
            "first_divergence_actor": ordered_keys[violating_indices[0]][1] if violating_indices else None,
            "divergence_mode": divergence_mode,
        }
        comparison_rows.append(
            {
                "category": "trace_field",
                "field": field,
                "role": field_role(field),
                "tolerance": tolerance,
                "max_abs_diff": max_abs_diff,
                "outside_tolerance_count": outside_tolerance,
                "divergence_mode": divergence_mode,
                "first_divergence_step_index": field_stats[field]["first_divergence_step_index"],
                "first_divergence_actor": field_stats[field]["first_divergence_actor"],
                "run_a_value": json.dumps(round_vector([normalise_value(field, indexed_a[ordered_keys[0]].get(field))]))
                if field not in TRACE_STRING_FIELDS and field not in TRACE_BOOLEAN_FIELDS and field not in TRACE_INTEGER_FIELDS
                else indexed_a[ordered_keys[0]].get(field),
                "run_b_value": json.dumps(round_vector([normalise_value(field, indexed_b[ordered_keys[0]].get(field))]))
                if field not in TRACE_STRING_FIELDS and field not in TRACE_BOOLEAN_FIELDS and field not in TRACE_INTEGER_FIELDS
                else indexed_b[ordered_keys[0]].get(field),
            }
        )

    summary = {
        "trace_row_count": len(rows_a),
        "completed_steps": len({int(row["step_index"]) for row in rows_a}),
        "actor_coverage": sorted({row["actor"] for row in rows_a}),
        "first_divergence": first_divergence,
        "field_statistics": field_stats,
        "diagnostic_fields_match": all(
            stats["outside_tolerance_count"] == 0 for field, stats in field_stats.items() if stats["role"] == "diagnostic"
        ),
        "authoritative_fields_match": all(
            stats["outside_tolerance_count"] == 0 for field, stats in field_stats.items() if stats["role"] == "authoritative"
        ),
        "state_fields_match": all(stats["outside_tolerance_count"] == 0 for stats in field_stats.values() if stats["role"] == "state"),
    }

    return summary, comparison_rows


def compare_summary_values(summary_a: dict[str, Any], summary_b: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    final_a = summary_a["final_state"]
    final_b = summary_b["final_state"]
    event_a = summary_a["event_steps"]
    event_b = summary_b["event_steps"]
    energy_a = summary_a["final_energy"]
    energy_b = summary_b["final_energy"]
    initial_energy_a = summary_a["initial_energy"]
    initial_energy_b = summary_b["initial_energy"]

    simulation_duration_a = float(summary_a["completed_steps"]) / float(summary_a["simulation"]["stepsPerSecond"])
    simulation_duration_b = float(summary_b["completed_steps"]) / float(summary_b["simulation"]["stepsPerSecond"])

    checks = {
        "completed_steps": summary_a["completed_steps"] == summary_b["completed_steps"],
        "simulation_duration_s": compare_scalar(simulation_duration_a, simulation_duration_b, TRACE_TOLERANCES["simulationTimeSeconds"]),
        "cube_final_position": compare_vector(final_a["cube"]["position_m"], final_b["cube"]["position_m"], TOLERANCES["finalPositionMeters"]),
        "sphere_final_position": compare_vector(final_a["sphere"]["position_m"], final_b["sphere"]["position_m"], TOLERANCES["finalPositionMeters"]),
        "cube_final_orientation": compare_vector(final_a["cube"]["orientation_quat"], final_b["cube"]["orientation_quat"], TRACE_TOLERANCES["orientationQuat"]),
        "sphere_final_orientation": compare_vector(final_a["sphere"]["orientation_quat"], final_b["sphere"]["orientation_quat"], TRACE_TOLERANCES["orientationQuat"]),
        "cube_final_linear_velocity": compare_vector(final_a["cube"]["linear_velocity_mps"], final_b["cube"]["linear_velocity_mps"], TOLERANCES["finalVelocityMetersPerSecond"]),
        "sphere_final_linear_velocity": compare_vector(final_a["sphere"]["linear_velocity_mps"], final_b["sphere"]["linear_velocity_mps"], TOLERANCES["finalVelocityMetersPerSecond"]),
        "cube_final_angular_velocity": compare_vector(final_a["cube"]["angular_velocity_rad_s"], final_b["cube"]["angular_velocity_rad_s"], TRACE_TOLERANCES["angularVelocityRadPerSec"]),
        "sphere_final_angular_velocity": compare_vector(final_a["sphere"]["angular_velocity_rad_s"], final_b["sphere"]["angular_velocity_rad_s"], TRACE_TOLERANCES["angularVelocityRadPerSec"]),
        "cube_final_total_speed": compare_scalar(float(final_a["cube"]["speed_mps"]), float(final_b["cube"]["speed_mps"]), TRACE_TOLERANCES["velocityMetersPerSecond"]),
        "sphere_final_total_speed": compare_scalar(float(final_a["sphere"]["speed_mps"]), float(final_b["sphere"]["speed_mps"]), TRACE_TOLERANCES["velocityMetersPerSecond"]),
        "cube_final_planar_speed": compare_scalar(float(final_a["cube"]["planar_speed_mps"]), float(final_b["cube"]["planar_speed_mps"]), TRACE_TOLERANCES["velocityMetersPerSecond"]),
        "sphere_final_planar_speed": compare_scalar(float(final_a["sphere"]["planar_speed_mps"]), float(final_b["sphere"]["planar_speed_mps"]), TRACE_TOLERANCES["velocityMetersPerSecond"]),
        "cube_final_angular_speed": compare_scalar(float(final_a["cube"]["angular_speed_rad_s"]), float(final_b["cube"]["angular_speed_rad_s"]), TRACE_TOLERANCES["angularSpeedRadPerSec"]),
        "sphere_final_angular_speed": compare_scalar(float(final_a["sphere"]["angular_speed_rad_s"]), float(final_b["sphere"]["angular_speed_rad_s"]), TRACE_TOLERANCES["angularSpeedRadPerSec"]),
        "cube_first_contact_step": abs(int(event_a["cube_first_contact_step"]) - int(event_b["cube_first_contact_step"])) <= TOLERANCES["contactStep"],
        "sphere_first_contact_step": abs(int(event_a["sphere_first_contact_step"]) - int(event_b["sphere_first_contact_step"])) <= TOLERANCES["contactStep"],
        "cube_first_sleep_step": abs(int(event_a["cube_first_sleep_step"]) - int(event_b["cube_first_sleep_step"])) <= TOLERANCES["settleStep"],
        "sphere_first_sleep_step": abs(int(event_a["sphere_first_sleep_step"]) - int(event_b["sphere_first_sleep_step"])) <= TOLERANCES["settleStep"],
        "cube_settle_step": abs(int(event_a["cube_settle_step"]) - int(event_b["cube_settle_step"])) <= TOLERANCES["settleStep"],
        "sphere_settle_step": abs(int(event_a["sphere_settle_step"]) - int(event_b["sphere_settle_step"])) <= TOLERANCES["settleStep"],
        "shared_settle_step": abs(int(event_a["run_settle_step"]) - int(event_b["run_settle_step"])) <= TOLERANCES["settleStep"],
        "first_rebound_step": abs(int(event_a["sphere_rebound_step"]) - int(event_b["sphere_rebound_step"])) <= TOLERANCES["contactStep"],
        "rebound_height_m": compare_scalar(float(event_a["sphere_rebound_height_m"]), float(event_b["sphere_rebound_height_m"]), TOLERANCES["reboundHeightMeters"]),
        "contact_counts": summary_a["contact_counts"] == summary_b["contact_counts"],
        "completion": summary_a["completion"] == summary_b["completion"],
        "pass_fail": summary_a["pass_fail"] == summary_b["pass_fail"],
        "status": summary_a["status"] == summary_b["status"],
        "failure_reason": summary_a["failure_reason"] == summary_b["failure_reason"],
        "cross_source_discrepancy_flags": summary_a["cross_source_discrepancy_flags"] == summary_b["cross_source_discrepancy_flags"],
    }

    summary_diffs: list[dict[str, Any]] = []

    def record_diff(path: tuple[str, ...], value_a: Any, value_b: Any) -> None:
        summary_diffs.append(
            {
                "path": ".".join(path),
                "run_a_value": value_a,
                "run_b_value": value_b,
                "classification": classify_summary_path(path),
            }
        )

    def recurse(path: tuple[str, ...], value_a: Any, value_b: Any) -> None:
        if isinstance(value_a, dict) and isinstance(value_b, dict):
            keys = sorted(set(value_a) | set(value_b))
            for key in keys:
                recurse(path + (key,), value_a.get(key), value_b.get(key))
            return
        if isinstance(value_a, list) and isinstance(value_b, list):
            if value_a != value_b:
                record_diff(path, value_a, value_b)
            return
        if value_a != value_b:
            record_diff(path, value_a, value_b)

    recurse(tuple(), summary_a, summary_b)

    return {
        "checks": checks,
        "summary_differences": summary_diffs,
    }, []


def classify_summary_path(path: tuple[str, ...]) -> str:
    if path in EXPECTED_METADATA_DIFFS:
        return "expected metadata difference"
    if path[:1] in {("final_state",), ("final_energy",), ("initial_energy",), ("event_steps",), ("completion",), ("contact_counts",), ("cross_source_discrepancy_flags",), ("settle_counters",), ("simulation",), ("world",), ("thresholds",), ("state_sources",), ("status",), ("failure_reason",), ("pass_fail",), ("contact_events",), ("authoritative_runtime_pose_source",), ("authoritative_runtime_velocity_source",), ("settlement_velocity_source",), ("physics_simulation_view_source",), ("angular_speed_formula",), ("final_30_step_ranges",)}:
        return "physics-bearing difference"
    if path[:2] in {("stage", "canonical_usda"), ("stage", "canonical_usd")}:
        return "physics-bearing difference"
    return "unexplained difference"


def compare_artifacts(run_a_dir: Path, run_b_dir: Path) -> dict[str, Any]:
    summary_a = read_json(run_a_dir / "summary.json")
    summary_b = read_json(run_b_dir / "summary.json")
    trace_fields_a, trace_a = load_trace(run_a_dir / "step_metrics.csv")
    trace_fields_b, trace_b = load_trace(run_b_dir / "step_metrics.csv")

    if trace_fields_a != trace_fields_b:
        fail(f"trace header mismatch: {trace_fields_a} != {trace_fields_b}")

    missing_a = required_columns_missing(trace_fields_a)
    if missing_a:
        fail(f"missing required CSV column: {missing_a[0]}")
    missing_b = required_columns_missing(trace_fields_b)
    if missing_b:
        fail(f"missing required CSV column: {missing_b[0]}")

    if len(trace_a) != len(trace_b):
        fail(f"trace length mismatch: {len(trace_a)} != {len(trace_b)}")

    print("PHYSICS_COMPARE: run-01 summary opened", flush=True)
    print("PHYSICS_COMPARE: run-02 summary opened", flush=True)

    summary_checks, _ = compare_summary_values(summary_a, summary_b)
    expected_metadata_differences = [
        entry for entry in summary_checks["summary_differences"] if entry["classification"] == "expected metadata difference"
    ]
    physics_bearing_differences = [
        entry for entry in summary_checks["summary_differences"] if entry["classification"] == "physics-bearing difference"
    ]
    unexplained_differences = [
        entry for entry in summary_checks["summary_differences"] if entry["classification"] == "unexplained difference"
    ]
    trace_summary, comparison_rows = compare_rows(trace_a, trace_b, trace_fields_a)

    run_a_stage = summary_a["stage"]
    run_b_stage = summary_b["stage"]

    stage_files = {
        "run_a_usda": Path(run_a_stage["snapshot_usda"]),
        "run_a_usd": Path(run_a_stage["snapshot_usd"]),
        "run_b_usda": Path(run_b_stage["snapshot_usda"]),
        "run_b_usd": Path(run_b_stage["snapshot_usd"]),
        "run_a_trace": run_a_dir / "step_metrics.csv",
        "run_b_trace": run_b_dir / "step_metrics.csv",
        "run_a_summary": run_a_dir / "summary.json",
        "run_b_summary": run_b_dir / "summary.json",
    }

    file_inventory = {
        name: {
            "path": str(path),
            "size": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for name, path in stage_files.items()
    }

    byte_level_equality = {
        "usda": file_inventory["run_a_usda"]["sha256"] == file_inventory["run_b_usda"]["sha256"],
        "usd": file_inventory["run_a_usd"]["sha256"] == file_inventory["run_b_usd"]["sha256"],
        "csv": file_inventory["run_a_trace"]["sha256"] == file_inventory["run_b_trace"]["sha256"],
        "json": file_inventory["run_a_summary"]["sha256"] == file_inventory["run_b_summary"]["sha256"],
    }

    artifact_hash_consistency = {
        "run_a": {
            "snapshot_usda": summary_a["artifact_hashes"]["snapshot_usda"] == file_inventory["run_a_usda"]["sha256"],
            "snapshot_usd": summary_a["artifact_hashes"]["snapshot_usd"] == file_inventory["run_a_usd"]["sha256"],
            "trace_csv": summary_a["artifact_hashes"]["trace_csv"] == file_inventory["run_a_trace"]["sha256"],
        },
        "run_b": {
            "snapshot_usda": summary_b["artifact_hashes"]["snapshot_usda"] == file_inventory["run_b_usda"]["sha256"],
            "snapshot_usd": summary_b["artifact_hashes"]["snapshot_usd"] == file_inventory["run_b_usd"]["sha256"],
            "trace_csv": summary_b["artifact_hashes"]["trace_csv"] == file_inventory["run_b_trace"]["sha256"],
        },
    }

    summary_hash_differences = {
        "run_a_summary_hash": file_inventory["run_a_summary"]["sha256"],
        "run_b_summary_hash": file_inventory["run_b_summary"]["sha256"],
        "run_a_trace_hash": file_inventory["run_a_trace"]["sha256"],
        "run_b_trace_hash": file_inventory["run_b_trace"]["sha256"],
        "run_a_usda_hash": file_inventory["run_a_usda"]["sha256"],
        "run_b_usda_hash": file_inventory["run_b_usda"]["sha256"],
        "run_a_usd_hash": file_inventory["run_a_usd"]["sha256"],
        "run_b_usd_hash": file_inventory["run_b_usd"]["sha256"],
    }

    run_a_summary_trace_consistency = {
        "cube_final_position": compare_vector(summary_a["final_state"]["cube"]["position_m"], [to_float(trace_a[-1]["cube_px"]), to_float(trace_a[-1]["cube_py"]), to_float(trace_a[-1]["cube_pz"])], TOLERANCES["finalPositionMeters"]),
        "sphere_final_position": compare_vector(summary_a["final_state"]["sphere"]["position_m"], [to_float(trace_a[-1]["sphere_px"]), to_float(trace_a[-1]["sphere_py"]), to_float(trace_a[-1]["sphere_pz"])], TOLERANCES["finalPositionMeters"]),
        "cube_final_linear_velocity": compare_vector(summary_a["final_state"]["cube"]["linear_velocity_mps"], [to_float(trace_a[-1]["cube_runtime_vx"]), to_float(trace_a[-1]["cube_runtime_vy"]), to_float(trace_a[-1]["cube_runtime_vz"])], TOLERANCES["finalVelocityMetersPerSecond"]),
        "sphere_final_linear_velocity": compare_vector(summary_a["final_state"]["sphere"]["linear_velocity_mps"], [to_float(trace_a[-1]["sphere_runtime_vx"]), to_float(trace_a[-1]["sphere_runtime_vy"]), to_float(trace_a[-1]["sphere_runtime_vz"])], TOLERANCES["finalVelocityMetersPerSecond"]),
    }
    run_b_summary_trace_consistency = {
        "cube_final_position": compare_vector(summary_b["final_state"]["cube"]["position_m"], [to_float(trace_b[-1]["cube_px"]), to_float(trace_b[-1]["cube_py"]), to_float(trace_b[-1]["cube_pz"])], TOLERANCES["finalPositionMeters"]),
        "sphere_final_position": compare_vector(summary_b["final_state"]["sphere"]["position_m"], [to_float(trace_b[-1]["sphere_px"]), to_float(trace_b[-1]["sphere_py"]), to_float(trace_b[-1]["sphere_pz"])], TOLERANCES["finalPositionMeters"]),
        "cube_final_linear_velocity": compare_vector(summary_b["final_state"]["cube"]["linear_velocity_mps"], [to_float(trace_b[-1]["cube_runtime_vx"]), to_float(trace_b[-1]["cube_runtime_vy"]), to_float(trace_b[-1]["cube_runtime_vz"])], TOLERANCES["finalVelocityMetersPerSecond"]),
        "sphere_final_linear_velocity": compare_vector(summary_b["final_state"]["sphere"]["linear_velocity_mps"], [to_float(trace_b[-1]["sphere_runtime_vx"]), to_float(trace_b[-1]["sphere_runtime_vy"]), to_float(trace_b[-1]["sphere_runtime_vz"])], TOLERANCES["finalVelocityMetersPerSecond"]),
    }

    semantic_equality = (
        all(summary_checks["checks"].values())
        and trace_summary["first_divergence"] is None
        and all(artifact_hash_consistency["run_a"].values())
        and all(artifact_hash_consistency["run_b"].values())
        and not physics_bearing_differences
        and not unexplained_differences
    )

    report = {
        "schema_version": "2.0",
        "run_a": {
            "run_id": summary_a["run_id"],
            "summary_hash": file_inventory["run_a_summary"]["sha256"],
            "trace_hash": file_inventory["run_a_trace"]["sha256"],
            "canonical_usda_hash": file_inventory["run_a_usda"]["sha256"],
            "canonical_usd_hash": file_inventory["run_a_usd"]["sha256"],
            "artifact_hashes": summary_a["artifact_hashes"],
            "file_inventory": {
                "summary": file_inventory["run_a_summary"],
                "trace": file_inventory["run_a_trace"],
                "usda": file_inventory["run_a_usda"],
                "usd": file_inventory["run_a_usd"],
            },
        },
        "run_b": {
            "run_id": summary_b["run_id"],
            "summary_hash": file_inventory["run_b_summary"]["sha256"],
            "trace_hash": file_inventory["run_b_trace"]["sha256"],
            "canonical_usda_hash": file_inventory["run_b_usda"]["sha256"],
            "canonical_usd_hash": file_inventory["run_b_usd"]["sha256"],
            "artifact_hashes": summary_b["artifact_hashes"],
            "file_inventory": {
                "summary": file_inventory["run_b_summary"],
                "trace": file_inventory["run_b_trace"],
                "usda": file_inventory["run_b_usda"],
                "usd": file_inventory["run_b_usd"],
            },
        },
        "byte_level_equality": byte_level_equality,
        "artifact_hash_consistency": artifact_hash_consistency,
        "semantic_equality": semantic_equality,
        "tolerances": {
            **dict(TOLERANCES),
            **TRACE_TOLERANCES,
        },
        "summary_validation": summary_checks,
        "trace_validation": trace_summary,
        "summary_trace_consistency": {
            "run_a": run_a_summary_trace_consistency,
            "run_b": run_b_summary_trace_consistency,
        },
        "contact_count_comparison": summary_a["contact_counts"] == summary_b["contact_counts"],
        "source_artifact_hashes": summary_hash_differences,
        "expected_metadata_differences": expected_metadata_differences,
        "physics_bearing_differences": physics_bearing_differences,
        "unexplained_differences": unexplained_differences,
        "pass_fail": "pass"
        if (
            all(summary_checks["checks"].values())
            and trace_summary["first_divergence"] is None
            and byte_level_equality["usda"]
            and byte_level_equality["usd"]
            and all(artifact_hash_consistency["run_a"].values())
            and all(artifact_hash_consistency["run_b"].values())
            and not physics_bearing_differences
            and not unexplained_differences
        )
        else "fail",
    }

    report["maximum_absolute_difference_per_field"] = {
        field: stats["max_abs_diff"] for field, stats in trace_summary["field_statistics"].items()
    }
    report["first_divergence"] = trace_summary["first_divergence"]
    report["field_statistics"] = trace_summary["field_statistics"]
    report["comparison_overview"] = {
        "trace_row_count": trace_summary["trace_row_count"],
        "completed_steps": trace_summary["completed_steps"],
        "actor_coverage": trace_summary["actor_coverage"],
        "diagnostic_fields_match": trace_summary["diagnostic_fields_match"],
        "authoritative_fields_match": trace_summary["authoritative_fields_match"],
        "state_fields_match": trace_summary["state_fields_match"],
    }
    return report, comparison_rows


def write_comparison_outputs(report: dict[str, Any], comparison_rows: list[dict[str, Any]]) -> None:
    write_json(RESULTS_DIR / "comparison.json", report)
    with (RESULTS_DIR / "comparison.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "category",
                "field",
                "role",
                "tolerance",
                "max_abs_diff",
                "outside_tolerance_count",
                "divergence_mode",
                "first_divergence_step_index",
                "first_divergence_actor",
                "run_a_value",
                "run_b_value",
            ],
        )
        writer.writeheader()
        for row in comparison_rows:
            writer.writerow(row)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare the two Phase 6 physics runs.")
    parser.add_argument("--run-a", default=str(RESULTS_DIR / "run-01"))
    parser.add_argument("--run-b", default=str(RESULTS_DIR / "run-02"))
    args = parser.parse_args(argv)

    run_a_dir = Path(args.run_a)
    run_b_dir = Path(args.run_b)
    if not run_a_dir.is_dir():
        fail(f"missing run directory: {run_a_dir}")
    if not run_b_dir.is_dir():
        fail(f"missing run directory: {run_b_dir}")

    report, comparison_rows = compare_artifacts(run_a_dir, run_b_dir)
    print("PHYSICS_COMPARE: tolerances validated", flush=True)
    write_comparison_outputs(report, comparison_rows)
    if report["pass_fail"] != "pass":
        fail(f"comparison failed: {report['first_divergence']}")
    print("PHYSICS_COMPARE: comparison passed", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
