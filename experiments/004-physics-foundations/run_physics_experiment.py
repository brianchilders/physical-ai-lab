from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import csv
import math
import shutil
import sys
import traceback

from isaacsim import SimulationApp


ROOT = Path(__file__).resolve().parent
from physics_common import (  # noqa: E402
    OUTPUT_DIR,
    RESULTS_DIR,
    RUN_IDS,
    SCENE_USDA,
    SCENE_USD,
    SIMULATION_SETTINGS,
    WORLD_METADATA,
    ensure_run_dirs,
    sha256_file,
    vector_magnitude,
    write_json,
)


APP_CONFIG = {"headless": True}
MAX_STEPS = SIMULATION_SETTINGS["maxSteps"]
STEPS_PER_SECOND = SIMULATION_SETTINGS["stepsPerSecond"]
SETTLE_WINDOW = SIMULATION_SETTINGS["settleWindow"]
DT = 1.0 / float(STEPS_PER_SECOND)

BODY_SPECS = {
    "cube": {
        "path": "/World/Actors/LowBounceCube",
        "mass": 2.0,
        "shape": "cube",
        "size": 0.5,
    },
    "sphere": {
        "path": "/World/Actors/HighBounceSphere",
        "mass": 1.0,
        "shape": "sphere",
        "radius": 0.25,
    },
}

CSV_FIELDS = [
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
]

DIAGNOSTIC_VELOCITY_TOLERANCE = 0.001
DIAGNOSTIC_POSITION_TOLERANCE = 0.001
DIAGNOSTIC_SLEEP_TOLERANCE = 0


def fail(message: str) -> None:
    print(f"PHYSICS: FAIL: {message}", flush=True)
    raise RuntimeError(message)


def normalize_event_type(raw_value) -> str:
    name = getattr(raw_value, "name", None)
    if isinstance(name, str):
        return name.lower()
    text = str(raw_value).lower()
    if "found" in text:
        return "contact_found"
    if "persists" in text:
        return "contact_persists"
    if "lost" in text:
        return "contact_lost"
    return text


def decode_sdf_path(value) -> str:
    try:
        from pxr import PhysicsSchemaTools

        if isinstance(value, int):
            return str(PhysicsSchemaTools.intToSdfPath(value))
    except Exception:
        pass
    return str(value)


def get_translate(UsdGeom, prim):
    xform = UsdGeom.Xformable(prim)
    for op in xform.GetOrderedXformOps():
        if op.GetOpType() == UsdGeom.XformOp.TypeTranslate:
            value = op.Get()
            return tuple(float(component) for component in value)
    return (0.0, 0.0, 0.0)


def get_sampled_body_state(UsdGeom, body_prim, body_api):
    position = get_translate(UsdGeom, body_prim)
    velocity = tuple(float(component) for component in body_api.GetVelocityAttr().Get())
    angular_velocity = tuple(float(component) for component in body_api.GetAngularVelocityAttr().Get())
    speed = vector_magnitude(velocity)
    planar_speed = math.sqrt(velocity[0] ** 2 + velocity[1] ** 2)
    vertical_speed = velocity[2]
    angular_speed_rad_s = vector_magnitude(angular_velocity)
    return position, velocity, angular_velocity, speed, planar_speed, vertical_speed, angular_speed_rad_s


def body_pose_from_runtime(transform_row):
    position = tuple(float(component) for component in transform_row[:3])
    orientation = tuple(float(component) for component in transform_row[3:7])
    return position, orientation


def get_runtime_body_state(runtime_view, body_index: int):
    transforms = runtime_view.get_transforms().numpy()
    velocities = runtime_view.get_velocities().numpy()

    transform_row = transforms[body_index]
    velocity_row = velocities[body_index]

    position, orientation = body_pose_from_runtime(transform_row)
    linear_velocity = tuple(float(component) for component in velocity_row[:3])
    angular_velocity = tuple(float(component) for component in velocity_row[3:6])
    speed = vector_magnitude(linear_velocity)
    planar_speed = math.sqrt(linear_velocity[0] ** 2 + linear_velocity[1] ** 2)
    vertical_speed = linear_velocity[2]
    angular_speed_rad_s = vector_magnitude(angular_velocity)
    return position, orientation, linear_velocity, angular_velocity, speed, planar_speed, vertical_speed, angular_speed_rad_s


def body_energy(spec, position, velocity, angular_speed_rad_s):
    mass = float(spec["mass"])
    speed = math.sqrt(sum(component * component for component in velocity))
    translational = 0.5 * mass * speed * speed
    z = float(position[2])
    potential = mass * 9.81 * max(0.0, z)
    total = translational + potential
    return translational, potential, total


def contact_name(event_type: str) -> str:
    if "found" in event_type:
        return "contact_found"
    if "persists" in event_type:
        return "contact_persists"
    if "lost" in event_type:
        return "contact_lost"
    return "contact_unknown"


def first_path_in_pair(paths, needle: str) -> bool:
    return any(needle in path for path in paths)


def create_runtime_sampler(stage, cube_path: str, sphere_path: str) -> RuntimeSampler:
    from pxr import PhysicsSchemaTools, UsdUtils
    from isaacsim.core.simulation_manager import SimulationManager
    from omni.physx import get_physx_simulation_interface

    cache = UsdUtils.StageCache.Get()
    stage_id = cache.GetId(stage).ToLongInt()
    simulation_view = SimulationManager.get_physics_simulation_view()
    if simulation_view is None:
        SimulationManager.initialize_physics()
        simulation_view = SimulationManager.get_physics_simulation_view()
    if simulation_view is None:
        fail("physics simulation view is not initialized")
    body_view = simulation_view.create_rigid_body_view([cube_path, sphere_path])
    if not body_view.check():
        fail("failed to create live rigid-body view for diagnostics")
    prim_paths = [str(path) for path in body_view.prim_paths]
    body_indices = {path: index for index, path in enumerate(prim_paths)}
    missing = [path for path in (cube_path, sphere_path) if path not in body_indices]
    if missing:
        fail(f"runtime rigid-body view missing expected prims: {missing}")
    if not hasattr(get_physx_simulation_interface(), "is_sleeping"):
        fail("installed PhysX simulation interface does not expose is_sleeping()")
    if not hasattr(body_view, "get_velocities") or not hasattr(body_view, "get_transforms"):
        fail("installed rigid-body view does not expose get_velocities() and get_transforms()")
    return RuntimeSampler(
        stage_id=stage_id,
        simulation_view=simulation_view,
        body_view=body_view,
        body_indices=body_indices,
        body_path_ints={
            cube_path: int(PhysicsSchemaTools.sdfPathToInt(cube_path)),
            sphere_path: int(PhysicsSchemaTools.sdfPathToInt(sphere_path)),
        },
        physx_simulation=get_physx_simulation_interface(),
        velocity_api="omni.physics.tensors.RigidBodyView.get_velocities()",
        sleep_api="omni.physx.IPhysxSimulation.is_sleeping(stage_id, body_path)",
        pose_api="omni.physics.tensors.RigidBodyView.get_transforms()",
        simulation_view_api="isaacsim.core.simulation_manager.SimulationManager.get_physics_simulation_view()",
    )


@dataclass
class BodySample:
    sampled_position: tuple[float, float, float]
    sampled_orientation: tuple[float, float, float, float]
    sampled_linear_velocity: tuple[float, float, float]
    sampled_angular_velocity: tuple[float, float, float]
    sampled_speed: float
    sampled_planar_speed: float
    sampled_vertical_speed: float
    sampled_angular_speed: float
    runtime_position: tuple[float, float, float]
    runtime_orientation: tuple[float, float, float, float]
    runtime_linear_velocity: tuple[float, float, float]
    runtime_angular_velocity: tuple[float, float, float]
    runtime_speed: float
    runtime_planar_speed: float
    runtime_vertical_speed: float
    runtime_angular_speed: float
    pose_linear_velocity: tuple[float, float, float] | None
    pose_speed: float | None
    sleeping: bool | None

    @property
    def position(self):
        return self.runtime_position

    @property
    def velocity(self):
        return self.runtime_linear_velocity

    @property
    def angular_velocity(self):
        return self.runtime_angular_velocity

    @property
    def speed(self):
        return self.runtime_speed

    @property
    def planar_speed(self):
        return self.runtime_planar_speed

    @property
    def vertical_speed(self):
        return self.runtime_vertical_speed

    @property
    def angular_speed(self):
        return self.runtime_angular_speed


@dataclass
class StepSample:
    step_index: int
    sim_time_s: float
    cube: BodySample
    sphere: BodySample
    cube_usd_sampled_kinetic_energy_j: float
    cube_usd_sampled_potential_energy_j: float
    cube_usd_sampled_total_mechanical_energy_j: float
    cube_runtime_kinetic_energy_j: float
    cube_runtime_potential_energy_j: float
    cube_runtime_total_mechanical_energy_j: float
    sphere_usd_sampled_kinetic_energy_j: float
    sphere_usd_sampled_potential_energy_j: float
    sphere_usd_sampled_total_mechanical_energy_j: float
    sphere_runtime_kinetic_energy_j: float
    sphere_runtime_potential_energy_j: float
    sphere_runtime_total_mechanical_energy_j: float
    cube_contact_found: bool
    cube_contact_persists: bool
    cube_contact_lost: bool
    sphere_contact_found: bool
    sphere_contact_persists: bool
    sphere_contact_lost: bool
    sphere_rebounded: bool
    cube_contact_active: bool
    sphere_contact_active: bool
    cube_settle_counter: int
    sphere_settle_counter: int
    run_settled: bool

    @property
    def cube_kinetic_energy_j(self):
        return self.cube_runtime_kinetic_energy_j

    @property
    def cube_potential_energy_j(self):
        return self.cube_runtime_potential_energy_j

    @property
    def cube_total_mechanical_energy_j(self):
        return self.cube_runtime_total_mechanical_energy_j

    @property
    def sphere_kinetic_energy_j(self):
        return self.sphere_runtime_kinetic_energy_j

    @property
    def sphere_potential_energy_j(self):
        return self.sphere_runtime_potential_energy_j

    @property
    def sphere_total_mechanical_energy_j(self):
        return self.sphere_runtime_total_mechanical_energy_j


@dataclass
class RunState:
    run_id: str
    output_dir: Path
    results_dir: Path
    step_samples: list[StepSample]
    contact_events: list[dict[str, object]]
    first_contact_step: dict[str, int | None]
    rebound_step: int | None
    rebound_height_m: float | None
    cube_settle_step: int | None
    sphere_settle_step: int | None
    run_settle_step: int | None
    run_settled: bool
    body_contact_active: dict[str, bool]
    body_contact_seen: dict[str, bool]
    body_contact_lost: dict[str, bool]
    first_contact_announced: dict[str, bool]
    rebound_announced: bool
    contact_counts: dict[str, dict[str, int]]
    post_contact_counters: dict[str, int]
    max_post_contact_counters: dict[str, int]
    body_contact_height: dict[str, float | None]
    body_peak_height: dict[str, float | None]
    body_first_vertical_speed: dict[str, float | None]
    first_sleep_step: dict[str, int | None]
    wake_step: dict[str, int | None]
    last_sleep_state: dict[str, bool | None]
    previous_runtime_position: dict[str, tuple[float, float, float] | None]
    previous_runtime_velocity: dict[str, tuple[float, float, float] | None]
    previous_runtime_vertical_velocity: dict[str, float | None]
    previous_sampled_velocity: dict[str, tuple[float, float, float] | None]


def init_run_state(run_id: str, output_dir: Path, results_dir: Path) -> RunState:
    return RunState(
        run_id=run_id,
        output_dir=output_dir,
        results_dir=results_dir,
        step_samples=[],
        contact_events=[],
        first_contact_step={"cube": None, "sphere": None},
        rebound_step=None,
        rebound_height_m=None,
        cube_settle_step=None,
        sphere_settle_step=None,
        run_settle_step=None,
        run_settled=False,
        body_contact_active={"cube": False, "sphere": False},
        body_contact_seen={"cube": False, "sphere": False},
        body_contact_lost={"cube": False, "sphere": False},
        first_contact_announced={"cube": False, "sphere": False},
        rebound_announced=False,
        contact_counts={
            "cube": {"contact_found": 0, "contact_persists": 0, "contact_lost": 0},
            "sphere": {"contact_found": 0, "contact_persists": 0, "contact_lost": 0},
        },
        post_contact_counters={"cube": 0, "sphere": 0},
        max_post_contact_counters={"cube": 0, "sphere": 0},
        body_contact_height={"cube": None, "sphere": None},
        body_peak_height={"cube": None, "sphere": None},
        body_first_vertical_speed={"cube": None, "sphere": None},
        first_sleep_step={"cube": None, "sphere": None},
        wake_step={"cube": None, "sphere": None},
        last_sleep_state={"cube": None, "sphere": None},
        previous_runtime_position={"cube": None, "sphere": None},
        previous_runtime_velocity={"cube": None, "sphere": None},
        previous_runtime_vertical_velocity={"cube": None, "sphere": None},
        previous_sampled_velocity={"cube": None, "sphere": None},
    )


@dataclass
class RuntimeSampler:
    stage_id: int
    simulation_view: object
    body_view: object
    body_indices: dict[str, int]
    body_path_ints: dict[str, int]
    physx_simulation: object
    simulation_view_api: str
    velocity_api: str
    sleep_api: str
    pose_api: str


def emit_diagnostic_line(run_id: str, sample: StepSample, reasons: list[str]) -> None:
    if not reasons:
        return
    print(
        (
            f"PHYSICS: {run_id} diagnostic "
            f"step={sample.step_index} "
            f"cube_planar={sample.cube.runtime_planar_speed:.6f} "
            f"cube_angular={sample.cube.runtime_angular_speed:.6f} "
            f"cube_settle={sample.cube_settle_counter} "
            f"sphere_total={sample.sphere.runtime_speed:.6f} "
            f"sphere_vz={sample.sphere.runtime_vertical_speed:.6f} "
            f"sphere_settle={sample.sphere_settle_counter} "
            f"cube_contact={int(sample.cube_contact_active)} "
            f"sphere_contact={int(sample.sphere_contact_active)} "
            f"rebound={int(sample.sphere_rebounded)} "
            f"reason={','.join(reasons)}"
        ),
        flush=True,
    )


def record_contact_event(state: RunState, step_index: int, header, data) -> list[str]:
    reasons: list[str] = []
    event_type = contact_name(normalize_event_type(getattr(header, "type", "")))
    actor0 = decode_sdf_path(getattr(header, "actor0", ""))
    actor1 = decode_sdf_path(getattr(header, "actor1", ""))
    collider0 = decode_sdf_path(getattr(header, "collider0", ""))
    collider1 = decode_sdf_path(getattr(header, "collider1", ""))

    impulse = 0.0
    offset = int(getattr(header, "contact_data_offset", 0))
    count = int(getattr(header, "num_contact_data", 0))
    for index in range(offset, offset + count):
        if index >= len(data):
            continue
        contact = data[index]
        contact_impulse = getattr(contact, "impulse", (0.0, 0.0, 0.0))
        impulse += math.sqrt(sum(float(component) * float(component) for component in contact_impulse))

    event = {
        "step_index": step_index,
        "event_type": event_type,
        "actor0": actor0,
        "actor1": actor1,
        "collider0": collider0,
        "collider1": collider1,
        "impulse": round(impulse, 6),
    }
    state.contact_events.append(event)

    tracked = {
        "cube": "/World/Actors/LowBounceCube",
        "sphere": "/World/Actors/HighBounceSphere",
    }
    for body_name, body_path in tracked.items():
        if first_path_in_pair((actor0, actor1, collider0, collider1), body_path):
            state.contact_counts[body_name][event_type] = state.contact_counts[body_name].get(event_type, 0) + 1
            state.body_contact_seen[body_name] = True
            state.body_contact_active[body_name] = event_type != "contact_lost"
            if event_type == "contact_lost":
                state.body_contact_lost[body_name] = True
            if state.first_contact_step[body_name] is None and event_type in {"contact_found", "contact_persists"}:
                state.first_contact_step[body_name] = step_index
                if not state.first_contact_announced[body_name]:
                    reasons.append(f"first_contact:{body_name}")
                    state.first_contact_announced[body_name] = True

    return reasons


def capture_step_sample(UsdGeom, cube_prim, sphere_prim, cube_api, sphere_api, runtime: RuntimeSampler, state: RunState, step_index: int) -> StepSample:
    def build_body_sample(body_name: str, body_prim, body_api) -> BodySample:
        sampled_position, sampled_velocity, sampled_angular_velocity, sampled_speed, sampled_planar_speed, sampled_vertical_speed, sampled_angular_speed = get_sampled_body_state(
            UsdGeom,
            body_prim,
            body_api,
        )
        runtime_position, runtime_orientation, runtime_linear_velocity, runtime_angular_velocity, runtime_speed, runtime_planar_speed, runtime_vertical_speed, runtime_angular_speed = get_runtime_body_state(
            runtime.body_view,
            runtime.body_indices[str(body_prim.GetPath())],
        )
        previous_runtime_position = state.previous_runtime_position[body_name]
        if previous_runtime_position is None:
            pose_linear_velocity = None
            pose_speed = None
        else:
            pose_linear_velocity = tuple((runtime_position[index] - previous_runtime_position[index]) / DT for index in range(3))
            pose_speed = vector_magnitude(pose_linear_velocity)
        state.previous_runtime_position[body_name] = runtime_position
        state.previous_runtime_velocity[body_name] = runtime_linear_velocity
        sleeping = bool(runtime.physx_simulation.is_sleeping(runtime.stage_id, runtime.body_path_ints[str(body_prim.GetPath())]))
        previous_sleeping = state.last_sleep_state[body_name]
        state.last_sleep_state[body_name] = sleeping
        if sleeping and state.first_sleep_step[body_name] is None:
            state.first_sleep_step[body_name] = step_index
        if previous_sleeping is True and sleeping is False:
            state.wake_step[body_name] = step_index
        return BodySample(
            sampled_position=sampled_position,
            sampled_orientation=(0.0, 0.0, 0.0, 1.0),
            sampled_linear_velocity=sampled_velocity,
            sampled_angular_velocity=sampled_angular_velocity,
            sampled_speed=sampled_speed,
            sampled_planar_speed=sampled_planar_speed,
            sampled_vertical_speed=sampled_vertical_speed,
            sampled_angular_speed=sampled_angular_speed,
            runtime_position=runtime_position,
            runtime_orientation=runtime_orientation,
            runtime_linear_velocity=runtime_linear_velocity,
            runtime_angular_velocity=runtime_angular_velocity,
            runtime_speed=runtime_speed,
            runtime_planar_speed=runtime_planar_speed,
            runtime_vertical_speed=runtime_vertical_speed,
            runtime_angular_speed=runtime_angular_speed,
            pose_linear_velocity=pose_linear_velocity,
            pose_speed=pose_speed,
            sleeping=sleeping,
        )

    cube_sample = build_body_sample("cube", cube_prim, cube_api)
    sphere_sample = build_body_sample("sphere", sphere_prim, sphere_api)

    cube_sampled_kinetic, cube_sampled_potential, cube_sampled_total = body_energy(BODY_SPECS["cube"], cube_sample.sampled_position, cube_sample.sampled_linear_velocity, cube_sample.sampled_angular_speed)
    cube_runtime_kinetic, cube_runtime_potential, cube_runtime_total = body_energy(BODY_SPECS["cube"], cube_sample.runtime_position, cube_sample.runtime_linear_velocity, cube_sample.runtime_angular_speed)
    sphere_sampled_kinetic, sphere_sampled_potential, sphere_sampled_total = body_energy(BODY_SPECS["sphere"], sphere_sample.sampled_position, sphere_sample.sampled_linear_velocity, sphere_sample.sampled_angular_speed)
    sphere_runtime_kinetic, sphere_runtime_potential, sphere_runtime_total = body_energy(BODY_SPECS["sphere"], sphere_sample.runtime_position, sphere_sample.runtime_linear_velocity, sphere_sample.runtime_angular_speed)

    if state.first_contact_step["sphere"] is not None:
        current_peak = state.body_peak_height["sphere"]
        if current_peak is None or sphere_sample.runtime_position[2] > current_peak:
            state.body_peak_height["sphere"] = sphere_sample.runtime_position[2]

    if state.first_contact_step["sphere"] is not None and state.body_contact_height["sphere"] is None:
        state.body_contact_height["sphere"] = sphere_sample.runtime_position[2]

    rebound_now = False
    if state.first_contact_step["sphere"] is not None and state.rebound_step is None:
        previous_vertical_velocity = state.previous_runtime_vertical_velocity["sphere"]
        if previous_vertical_velocity is not None and previous_vertical_velocity <= 0.0 and sphere_sample.runtime_vertical_speed > 0.0 and sphere_sample.runtime_position[2] > float(state.body_contact_height["sphere"] or 0.0) + 0.001:
            state.rebound_step = step_index
            peak = float(state.body_peak_height["sphere"] or sphere_sample.runtime_position[2])
            contact_height = float(state.body_contact_height["sphere"] or sphere_sample.runtime_position[2])
            state.rebound_height_m = max(0.0, peak - contact_height)
            rebound_now = True

    if state.first_contact_step["cube"] is not None:
        if cube_sample.runtime_planar_speed <= 0.02 and cube_sample.runtime_angular_speed <= 0.05:
            state.post_contact_counters["cube"] += 1
        else:
            state.post_contact_counters["cube"] = 0
    if state.first_contact_step["sphere"] is not None and state.rebound_step is not None:
        if sphere_sample.runtime_speed <= 0.02:
            state.post_contact_counters["sphere"] += 1
        else:
            state.post_contact_counters["sphere"] = 0

    state.max_post_contact_counters["cube"] = max(state.max_post_contact_counters["cube"], state.post_contact_counters["cube"])
    state.max_post_contact_counters["sphere"] = max(state.max_post_contact_counters["sphere"], state.post_contact_counters["sphere"])

    if state.cube_settle_step is None and state.post_contact_counters["cube"] >= SETTLE_WINDOW:
        state.cube_settle_step = step_index
    if state.sphere_settle_step is None and state.post_contact_counters["sphere"] >= SETTLE_WINDOW:
        state.sphere_settle_step = step_index
    if (
        not state.run_settled
        and state.post_contact_counters["cube"] >= SETTLE_WINDOW
        and state.post_contact_counters["sphere"] >= SETTLE_WINDOW
        and state.first_contact_step["cube"] is not None
        and state.first_contact_step["sphere"] is not None
        and state.rebound_step is not None
    ):
        state.run_settle_step = step_index
        state.run_settled = True

    state.previous_runtime_vertical_velocity["cube"] = cube_sample.runtime_vertical_speed
    state.previous_runtime_vertical_velocity["sphere"] = sphere_sample.runtime_vertical_speed

    sample = StepSample(
        step_index=step_index,
        sim_time_s=round(step_index * DT, 6),
        cube=cube_sample,
        sphere=sphere_sample,
        cube_usd_sampled_kinetic_energy_j=cube_sampled_kinetic,
        cube_usd_sampled_potential_energy_j=cube_sampled_potential,
        cube_usd_sampled_total_mechanical_energy_j=cube_sampled_total,
        cube_runtime_kinetic_energy_j=cube_runtime_kinetic,
        cube_runtime_potential_energy_j=cube_runtime_potential,
        cube_runtime_total_mechanical_energy_j=cube_runtime_total,
        sphere_usd_sampled_kinetic_energy_j=sphere_sampled_kinetic,
        sphere_usd_sampled_potential_energy_j=sphere_sampled_potential,
        sphere_usd_sampled_total_mechanical_energy_j=sphere_sampled_total,
        sphere_runtime_kinetic_energy_j=sphere_runtime_kinetic,
        sphere_runtime_potential_energy_j=sphere_runtime_potential,
        sphere_runtime_total_mechanical_energy_j=sphere_runtime_total,
        cube_contact_found=state.first_contact_step["cube"] == step_index,
        cube_contact_persists=state.body_contact_active["cube"] and state.first_contact_step["cube"] is not None and state.first_contact_step["cube"] < step_index,
        cube_contact_lost=state.body_contact_lost["cube"],
        sphere_contact_found=state.first_contact_step["sphere"] == step_index,
        sphere_contact_persists=state.body_contact_active["sphere"] and state.first_contact_step["sphere"] is not None and state.first_contact_step["sphere"] < step_index,
        sphere_contact_lost=state.body_contact_lost["sphere"],
        sphere_rebounded=state.rebound_step == step_index,
        cube_contact_active=state.body_contact_active["cube"],
        sphere_contact_active=state.body_contact_active["sphere"],
        cube_settle_counter=state.post_contact_counters["cube"],
        sphere_settle_counter=state.post_contact_counters["sphere"],
        run_settled=state.run_settled,
    )
    state.step_samples.append(sample)
    return sample


def sample_contact_state(sample: StepSample, body_name: str) -> str:
    if body_name == "cube":
        if sample.cube_contact_found:
            return "contact_found"
        if sample.cube_contact_persists:
            return "contact_persists"
        if sample.cube_contact_lost:
            return "contact_lost"
        return "no_contact"
    if sample.sphere_contact_found:
        return "contact_found"
    if sample.sphere_contact_persists:
        return "contact_persists"
    if sample.sphere_contact_lost:
        return "contact_lost"
    return "no_contact"


def build_actor_row(run_id: str, sample: StepSample, body_name: str) -> dict[str, object]:
    body = sample.cube if body_name == "cube" else sample.sphere
    prefix = "cube" if body_name == "cube" else "sphere"
    contact_found = sample.cube_contact_found if body_name == "cube" else sample.sphere_contact_found
    contact_persists = sample.cube_contact_persists if body_name == "cube" else sample.sphere_contact_persists
    contact_lost = sample.cube_contact_lost if body_name == "cube" else sample.sphere_contact_lost
    settle_counter = sample.cube_settle_counter if body_name == "cube" else sample.sphere_settle_counter
    rebound_state = int(sample.sphere_rebounded if body_name == "sphere" else False)

    return {
        "run_id": run_id,
        "step_index": sample.step_index,
        "sim_time_s": round(sample.sim_time_s, 6),
        "actor": body_name,
        "position_x_m": round(body.runtime_position[0], 6),
        "position_y_m": round(body.runtime_position[1], 6),
        "position_z_m": round(body.runtime_position[2], 6),
        "orientation_x": round(body.runtime_orientation[0], 6),
        "orientation_y": round(body.runtime_orientation[1], 6),
        "orientation_z": round(body.runtime_orientation[2], 6),
        "orientation_w": round(body.runtime_orientation[3], 6),
        "usd_sampled_linear_velocity_x_mps": round(body.sampled_linear_velocity[0], 6),
        "usd_sampled_linear_velocity_y_mps": round(body.sampled_linear_velocity[1], 6),
        "usd_sampled_linear_velocity_z_mps": round(body.sampled_linear_velocity[2], 6),
        "usd_sampled_vertical_velocity_mps": round(body.sampled_vertical_speed, 6),
        "usd_sampled_total_speed_mps": round(body.sampled_speed, 6),
        "usd_sampled_planar_speed_mps": round(body.sampled_planar_speed, 6),
        "usd_sampled_angular_velocity_x_rad_s": round(body.sampled_angular_velocity[0], 6),
        "usd_sampled_angular_velocity_y_rad_s": round(body.sampled_angular_velocity[1], 6),
        "usd_sampled_angular_velocity_z_rad_s": round(body.sampled_angular_velocity[2], 6),
        "usd_sampled_angular_speed_rad_s": round(body.sampled_angular_speed, 6),
        "runtime_linear_velocity_x_mps": round(body.runtime_linear_velocity[0], 6),
        "runtime_linear_velocity_y_mps": round(body.runtime_linear_velocity[1], 6),
        "runtime_linear_velocity_z_mps": round(body.runtime_linear_velocity[2], 6),
        "runtime_vertical_velocity_mps": round(body.runtime_vertical_speed, 6),
        "runtime_total_speed_mps": round(body.runtime_speed, 6),
        "runtime_planar_speed_mps": round(body.runtime_planar_speed, 6),
        "runtime_angular_velocity_x_rad_s": round(body.runtime_angular_velocity[0], 6),
        "runtime_angular_velocity_y_rad_s": round(body.runtime_angular_velocity[1], 6),
        "runtime_angular_velocity_z_rad_s": round(body.runtime_angular_velocity[2], 6),
        "runtime_angular_speed_rad_s": round(body.runtime_angular_speed, 6),
        "pose_linear_velocity_x_mps": None if body.pose_linear_velocity is None else round(body.pose_linear_velocity[0], 6),
        "pose_linear_velocity_y_mps": None if body.pose_linear_velocity is None else round(body.pose_linear_velocity[1], 6),
        "pose_linear_velocity_z_mps": None if body.pose_linear_velocity is None else round(body.pose_linear_velocity[2], 6),
        "pose_speed_mps": None if body.pose_speed is None else round(body.pose_speed, 6),
        "sleeping": int(body.sleeping) if body.sleeping is not None else None,
        "contact_state": sample_contact_state(sample, body_name),
        "contact_found": int(contact_found),
        "contact_persists": int(contact_persists),
        "contact_lost": int(contact_lost),
        "contact_active": int(sample.cube_contact_active if body_name == "cube" else sample.sphere_contact_active),
        "settle_counter": settle_counter,
        "rebound_state": rebound_state,
        "usd_sampled_kinetic_energy_j": round(sample.cube_usd_sampled_kinetic_energy_j if body_name == "cube" else sample.sphere_usd_sampled_kinetic_energy_j, 6),
        "usd_sampled_potential_energy_j": round(sample.cube_usd_sampled_potential_energy_j if body_name == "cube" else sample.sphere_usd_sampled_potential_energy_j, 6),
        "usd_sampled_total_mechanical_energy_j": round(sample.cube_usd_sampled_total_mechanical_energy_j if body_name == "cube" else sample.sphere_usd_sampled_total_mechanical_energy_j, 6),
        "runtime_kinetic_energy_j": round(sample.cube_runtime_kinetic_energy_j if body_name == "cube" else sample.sphere_runtime_kinetic_energy_j, 6),
        "runtime_potential_energy_j": round(sample.cube_runtime_potential_energy_j if body_name == "cube" else sample.sphere_runtime_potential_energy_j, 6),
        "runtime_total_mechanical_energy_j": round(sample.cube_runtime_total_mechanical_energy_j if body_name == "cube" else sample.sphere_runtime_total_mechanical_energy_j, 6),
        "cube_px": round(sample.cube.runtime_position[0], 6),
        "cube_py": round(sample.cube.runtime_position[1], 6),
        "cube_pz": round(sample.cube.runtime_position[2], 6),
        "cube_orientation_x": round(sample.cube.runtime_orientation[0], 6),
        "cube_orientation_y": round(sample.cube.runtime_orientation[1], 6),
        "cube_orientation_z": round(sample.cube.runtime_orientation[2], 6),
        "cube_orientation_w": round(sample.cube.runtime_orientation[3], 6),
        "cube_usd_sampled_vx": round(sample.cube.sampled_linear_velocity[0], 6),
        "cube_usd_sampled_vy": round(sample.cube.sampled_linear_velocity[1], 6),
        "cube_usd_sampled_vz": round(sample.cube.sampled_linear_velocity[2], 6),
        "cube_usd_sampled_speed_mps": round(sample.cube.sampled_speed, 6),
        "cube_usd_sampled_planar_speed_mps": round(sample.cube.sampled_planar_speed, 6),
        "cube_usd_sampled_vertical_speed_mps": round(sample.cube.sampled_vertical_speed, 6),
        "cube_usd_sampled_wx_rad_s": round(sample.cube.sampled_angular_velocity[0], 6),
        "cube_usd_sampled_wy_rad_s": round(sample.cube.sampled_angular_velocity[1], 6),
        "cube_usd_sampled_wz_rad_s": round(sample.cube.sampled_angular_velocity[2], 6),
        "cube_usd_sampled_angular_speed_rad_s": round(sample.cube.sampled_angular_speed, 6),
        "cube_runtime_vx": round(sample.cube.runtime_linear_velocity[0], 6),
        "cube_runtime_vy": round(sample.cube.runtime_linear_velocity[1], 6),
        "cube_runtime_vz": round(sample.cube.runtime_linear_velocity[2], 6),
        "cube_runtime_speed_mps": round(sample.cube.runtime_speed, 6),
        "cube_runtime_planar_speed_mps": round(sample.cube.runtime_planar_speed, 6),
        "cube_runtime_vertical_speed_mps": round(sample.cube.runtime_vertical_speed, 6),
        "cube_runtime_wx_rad_s": round(sample.cube.runtime_angular_velocity[0], 6),
        "cube_runtime_wy_rad_s": round(sample.cube.runtime_angular_velocity[1], 6),
        "cube_runtime_wz_rad_s": round(sample.cube.runtime_angular_velocity[2], 6),
        "cube_runtime_angular_speed_rad_s": round(sample.cube.runtime_angular_speed, 6),
        "cube_pose_vx": None if sample.cube.pose_linear_velocity is None else round(sample.cube.pose_linear_velocity[0], 6),
        "cube_pose_vy": None if sample.cube.pose_linear_velocity is None else round(sample.cube.pose_linear_velocity[1], 6),
        "cube_pose_vz": None if sample.cube.pose_linear_velocity is None else round(sample.cube.pose_linear_velocity[2], 6),
        "cube_pose_speed_mps": None if sample.cube.pose_speed is None else round(sample.cube.pose_speed, 6),
        "cube_sleeping": int(sample.cube.sleeping) if sample.cube.sleeping is not None else None,
        "cube_contact_found": int(sample.cube_contact_found),
        "cube_contact_persists": int(sample.cube_contact_persists),
        "cube_contact_lost": int(sample.cube_contact_lost),
        "sphere_px": round(sample.sphere.runtime_position[0], 6),
        "sphere_py": round(sample.sphere.runtime_position[1], 6),
        "sphere_pz": round(sample.sphere.runtime_position[2], 6),
        "sphere_orientation_x": round(sample.sphere.runtime_orientation[0], 6),
        "sphere_orientation_y": round(sample.sphere.runtime_orientation[1], 6),
        "sphere_orientation_z": round(sample.sphere.runtime_orientation[2], 6),
        "sphere_orientation_w": round(sample.sphere.runtime_orientation[3], 6),
        "sphere_usd_sampled_vx": round(sample.sphere.sampled_linear_velocity[0], 6),
        "sphere_usd_sampled_vy": round(sample.sphere.sampled_linear_velocity[1], 6),
        "sphere_usd_sampled_vz": round(sample.sphere.sampled_linear_velocity[2], 6),
        "sphere_usd_sampled_speed_mps": round(sample.sphere.sampled_speed, 6),
        "sphere_usd_sampled_planar_speed_mps": round(sample.sphere.sampled_planar_speed, 6),
        "sphere_usd_sampled_vertical_speed_mps": round(sample.sphere.sampled_vertical_speed, 6),
        "sphere_usd_sampled_wx_rad_s": round(sample.sphere.sampled_angular_velocity[0], 6),
        "sphere_usd_sampled_wy_rad_s": round(sample.sphere.sampled_angular_velocity[1], 6),
        "sphere_usd_sampled_wz_rad_s": round(sample.sphere.sampled_angular_velocity[2], 6),
        "sphere_usd_sampled_angular_speed_rad_s": round(sample.sphere.sampled_angular_speed, 6),
        "sphere_runtime_vx": round(sample.sphere.runtime_linear_velocity[0], 6),
        "sphere_runtime_vy": round(sample.sphere.runtime_linear_velocity[1], 6),
        "sphere_runtime_vz": round(sample.sphere.runtime_linear_velocity[2], 6),
        "sphere_runtime_speed_mps": round(sample.sphere.runtime_speed, 6),
        "sphere_runtime_planar_speed_mps": round(sample.sphere.runtime_planar_speed, 6),
        "sphere_runtime_vertical_speed_mps": round(sample.sphere.runtime_vertical_speed, 6),
        "sphere_runtime_wx_rad_s": round(sample.sphere.runtime_angular_velocity[0], 6),
        "sphere_runtime_wy_rad_s": round(sample.sphere.runtime_angular_velocity[1], 6),
        "sphere_runtime_wz_rad_s": round(sample.sphere.runtime_angular_velocity[2], 6),
        "sphere_runtime_angular_speed_rad_s": round(sample.sphere.runtime_angular_speed, 6),
        "sphere_pose_vx": None if sample.sphere.pose_linear_velocity is None else round(sample.sphere.pose_linear_velocity[0], 6),
        "sphere_pose_vy": None if sample.sphere.pose_linear_velocity is None else round(sample.sphere.pose_linear_velocity[1], 6),
        "sphere_pose_vz": None if sample.sphere.pose_linear_velocity is None else round(sample.sphere.pose_linear_velocity[2], 6),
        "sphere_pose_speed_mps": None if sample.sphere.pose_speed is None else round(sample.sphere.pose_speed, 6),
        "sphere_sleeping": int(sample.sphere.sleeping) if sample.sphere.sleeping is not None else None,
        "sphere_contact_found": int(sample.sphere_contact_found),
        "sphere_contact_persists": int(sample.sphere_contact_persists),
        "sphere_contact_lost": int(sample.sphere_contact_lost),
        "sphere_rebounded": int(sample.sphere_rebounded),
        "run_settled": int(sample.run_settled),
    }


def build_trace_rows(run_id: str, state: RunState) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for sample in state.step_samples:
        rows.append(build_actor_row(run_id, sample, "cube"))
        rows.append(build_actor_row(run_id, sample, "sphere"))
    return rows


def save_trace(run_results_dir: Path, run_id: str, state: RunState) -> Path:
    trace_path = run_results_dir / "step_metrics.csv"
    with trace_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(build_trace_rows(run_id, state))
    return trace_path


def final_sample(state: RunState) -> StepSample | None:
    return state.step_samples[-1] if state.step_samples else None


def sample_to_body_payload(sample: StepSample | None, body_name: str) -> dict[str, object]:
    if sample is None:
        return {
            "position_m": None,
            "linear_velocity_mps": None,
            "angular_velocity_rad_s": None,
            "speed_mps": None,
            "planar_speed_mps": None,
            "vertical_speed_mps": None,
            "angular_speed_rad_s": None,
            "kinetic_energy_j": None,
            "potential_energy_j": None,
            "total_mechanical_energy_j": None,
        }
    body = sample.cube if body_name == "cube" else sample.sphere
    sampled_kinetic = sample.cube_usd_sampled_kinetic_energy_j if body_name == "cube" else sample.sphere_usd_sampled_kinetic_energy_j
    sampled_potential = sample.cube_usd_sampled_potential_energy_j if body_name == "cube" else sample.sphere_usd_sampled_potential_energy_j
    sampled_total = sample.cube_usd_sampled_total_mechanical_energy_j if body_name == "cube" else sample.sphere_usd_sampled_total_mechanical_energy_j
    runtime_kinetic = sample.cube_runtime_kinetic_energy_j if body_name == "cube" else sample.sphere_runtime_kinetic_energy_j
    runtime_potential = sample.cube_runtime_potential_energy_j if body_name == "cube" else sample.sphere_runtime_potential_energy_j
    runtime_total = sample.cube_runtime_total_mechanical_energy_j if body_name == "cube" else sample.sphere_runtime_total_mechanical_energy_j
    return {
        "position_m": [round(value, 6) for value in body.runtime_position],
        "orientation_quat": [round(value, 6) for value in body.runtime_orientation],
        "linear_velocity_mps": [round(value, 6) for value in body.runtime_linear_velocity],
        "angular_velocity_rad_s": [round(value, 6) for value in body.runtime_angular_velocity],
        "speed_mps": round(body.runtime_speed, 6),
        "planar_speed_mps": round(body.runtime_planar_speed, 6),
        "vertical_speed_mps": round(body.runtime_vertical_speed, 6),
        "angular_speed_rad_s": round(body.runtime_angular_speed, 6),
        "kinetic_energy_j": round(runtime_kinetic, 6),
        "potential_energy_j": round(runtime_potential, 6),
        "total_mechanical_energy_j": round(runtime_total, 6),
        "sampled": {
            "position_m": [round(value, 6) for value in body.sampled_position],
            "linear_velocity_mps": [round(value, 6) for value in body.sampled_linear_velocity],
            "angular_velocity_rad_s": [round(value, 6) for value in body.sampled_angular_velocity],
            "speed_mps": round(body.sampled_speed, 6),
            "planar_speed_mps": round(body.sampled_planar_speed, 6),
            "vertical_speed_mps": round(body.sampled_vertical_speed, 6),
            "angular_speed_rad_s": round(body.sampled_angular_speed, 6),
            "kinetic_energy_j": round(sampled_kinetic, 6),
            "potential_energy_j": round(sampled_potential, 6),
            "total_mechanical_energy_j": round(sampled_total, 6),
        },
        "runtime": {
            "position_m": [round(value, 6) for value in body.runtime_position],
            "linear_velocity_mps": [round(value, 6) for value in body.runtime_linear_velocity],
            "angular_velocity_rad_s": [round(value, 6) for value in body.runtime_angular_velocity],
            "speed_mps": round(body.runtime_speed, 6),
            "planar_speed_mps": round(body.runtime_planar_speed, 6),
            "vertical_speed_mps": round(body.runtime_vertical_speed, 6),
            "angular_speed_rad_s": round(body.runtime_angular_speed, 6),
            "kinetic_energy_j": round(runtime_kinetic, 6),
            "potential_energy_j": round(runtime_potential, 6),
            "total_mechanical_energy_j": round(runtime_total, 6),
        },
        "pose": {
            "linear_velocity_mps": None if body.pose_linear_velocity is None else [round(value, 6) for value in body.pose_linear_velocity],
            "speed_mps": None if body.pose_speed is None else round(body.pose_speed, 6),
        },
        "sleeping": body.sleeping,
    }


def build_ranges(state: RunState) -> dict[str, object]:
    window = state.step_samples[-30:]
    cube_planar = [sample.cube.runtime_planar_speed for sample in window]
    cube_angular = [sample.cube.runtime_angular_speed for sample in window]
    sphere_total = [sample.sphere.runtime_speed for sample in window]
    sphere_vertical = [sample.sphere.runtime_vertical_speed for sample in window]
    return {
        "cube_planar_speed_mps": {
            "min": round(min(cube_planar), 6) if cube_planar else None,
            "max": round(max(cube_planar), 6) if cube_planar else None,
        },
        "cube_angular_speed_rad_s": {
            "min": round(min(cube_angular), 6) if cube_angular else None,
            "max": round(max(cube_angular), 6) if cube_angular else None,
        },
        "sphere_total_speed_mps": {
            "min": round(min(sphere_total), 6) if sphere_total else None,
            "max": round(max(sphere_total), 6) if sphere_total else None,
        },
        "sphere_vertical_velocity_mps": {
            "min": round(min(sphere_vertical), 6) if sphere_vertical else None,
            "max": round(max(sphere_vertical), 6) if sphere_vertical else None,
        },
    }


def build_unmet_conditions(state: RunState) -> list[str]:
    unmet: list[str] = []
    if state.first_contact_step["cube"] is None:
        unmet.append("cube never contacted the ground")
    if state.first_contact_step["sphere"] is None:
        unmet.append("sphere never contacted the ground")
    if state.rebound_step is None:
        unmet.append("sphere never completed a qualifying rebound")
    if state.cube_settle_step is None:
        unmet.append("cube did not satisfy the settling window")
    if state.sphere_settle_step is None:
        unmet.append("sphere did not satisfy the settling window")
    return unmet


def range_bounds(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"min": None, "max": None}
    return {"min": round(min(values), 6), "max": round(max(values), 6)}


def vector_range_bounds(vectors: list[tuple[float, float, float]]) -> dict[str, object]:
    if not vectors:
        return {
            "min": None,
            "max": None,
            "speed": {"min": None, "max": None},
        }
    return {
        "min": [round(min(values), 6) for values in zip(*vectors)],
        "max": [round(max(values), 6) for values in zip(*vectors)],
        "speed": range_bounds([vector_magnitude(vector) for vector in vectors]),
    }


def bool_range(values: list[bool]) -> dict[str, int | None]:
    if not values:
        return {"min": None, "max": None}
    ints = [int(value) for value in values]
    return {"min": min(ints), "max": max(ints)}


def build_final_window_diagnostics(state: RunState) -> dict[str, object]:
    window = state.step_samples[-30:]
    diagnostics: dict[str, object] = {}
    for body_name in ("cube", "sphere"):
        body_samples = [sample.cube if body_name == "cube" else sample.sphere for sample in window]
        sampled_linear = [body.sampled_linear_velocity for body in body_samples]
        runtime_linear = [body.runtime_linear_velocity for body in body_samples]
        pose_linear = [body.pose_linear_velocity for body in body_samples if body.pose_linear_velocity is not None]
        positions = [body.runtime_position for body in body_samples]
        displacements = []
        for current, previous in zip(positions[1:], positions[:-1]):
            displacements.append(vector_magnitude(tuple(current[index] - previous[index] for index in range(3))))
        sampled_speeds = [body.sampled_speed for body in body_samples]
        runtime_speeds = [body.runtime_speed for body in body_samples]
        pose_speeds = [body.pose_speed for body in body_samples if body.pose_speed is not None]
        sampled_vertical = [body.sampled_vertical_speed for body in body_samples]
        runtime_vertical = [body.runtime_vertical_speed for body in body_samples]
        pose_vertical = [body.pose_linear_velocity[2] for body in body_samples if body.pose_linear_velocity is not None]
        sampled_angular_speeds = [body.sampled_angular_speed for body in body_samples]
        runtime_angular_speeds = [body.runtime_angular_speed for body in body_samples]
        sleeping = [bool(body.sleeping) for body in body_samples if body.sleeping is not None]
        diagnostics[body_name] = {
            "position_m": vector_range_bounds(positions),
            "position_delta_m": {
                "min": round(min(displacements), 6) if displacements else None,
                "max": round(max(displacements), 6) if displacements else None,
            },
            "max_position_delta_m": round(max(displacements), 6) if displacements else None,
            "usd_sampled_linear_velocity_mps": vector_range_bounds(sampled_linear),
            "runtime_linear_velocity_mps": vector_range_bounds(runtime_linear),
            "pose_linear_velocity_mps": vector_range_bounds(pose_linear) if pose_linear else {"min": None, "max": None, "speed": {"min": None, "max": None}},
            "usd_sampled_speed_mps": range_bounds(sampled_speeds),
            "runtime_speed_mps": range_bounds(runtime_speeds),
            "pose_speed_mps": range_bounds(pose_speeds),
            "usd_sampled_vertical_velocity_mps": range_bounds(sampled_vertical),
            "runtime_vertical_velocity_mps": range_bounds(runtime_vertical),
            "pose_vertical_velocity_mps": range_bounds(pose_vertical),
            "usd_sampled_angular_speed_rad_s": range_bounds(sampled_angular_speeds),
            "runtime_angular_speed_rad_s": range_bounds(runtime_angular_speeds),
            "sleeping": bool_range(sleeping) if sleeping else {"min": None, "max": None},
        }
    diagnostics["discrepancy_flags"] = {
        "cube": {
            "sampled_vs_runtime_velocity_mismatch": any(
                vector_magnitude(tuple(a - b for a, b in zip(sample.cube.sampled_linear_velocity, sample.cube.runtime_linear_velocity))) > DIAGNOSTIC_VELOCITY_TOLERANCE
                for sample in window
            ),
            "sampled_vs_pose_velocity_mismatch": any(
                sample.cube.pose_linear_velocity is not None
                and vector_magnitude(tuple(a - b for a, b in zip(sample.cube.sampled_linear_velocity, sample.cube.pose_linear_velocity))) > DIAGNOSTIC_VELOCITY_TOLERANCE
                for sample in window
            ),
            "runtime_vs_pose_velocity_mismatch": any(
                sample.cube.pose_linear_velocity is not None
                and vector_magnitude(tuple(a - b for a, b in zip(sample.cube.runtime_linear_velocity, sample.cube.pose_linear_velocity))) > DIAGNOSTIC_VELOCITY_TOLERANCE
                for sample in window
            ),
            "sleeping_with_nonzero_sampled_velocity": any(
                bool(sample.cube.sleeping) and sample.cube.sampled_speed > DIAGNOSTIC_VELOCITY_TOLERANCE
                for sample in window
            ),
        },
        "sphere": {
            "sampled_vs_runtime_velocity_mismatch": any(
                vector_magnitude(tuple(a - b for a, b in zip(sample.sphere.sampled_linear_velocity, sample.sphere.runtime_linear_velocity))) > DIAGNOSTIC_VELOCITY_TOLERANCE
                for sample in window
            ),
            "sampled_vs_pose_velocity_mismatch": any(
                sample.sphere.pose_linear_velocity is not None
                and vector_magnitude(tuple(a - b for a, b in zip(sample.sphere.sampled_linear_velocity, sample.sphere.pose_linear_velocity))) > DIAGNOSTIC_VELOCITY_TOLERANCE
                for sample in window
            ),
            "runtime_vs_pose_velocity_mismatch": any(
                sample.sphere.pose_linear_velocity is not None
                and vector_magnitude(tuple(a - b for a, b in zip(sample.sphere.runtime_linear_velocity, sample.sphere.pose_linear_velocity))) > DIAGNOSTIC_VELOCITY_TOLERANCE
                for sample in window
            ),
            "sleeping_with_nonzero_sampled_velocity": any(
                bool(sample.sphere.sleeping) and sample.sphere.sampled_speed > DIAGNOSTIC_VELOCITY_TOLERANCE
                for sample in window
            ),
        },
        "tolerance": DIAGNOSTIC_VELOCITY_TOLERANCE,
    }
    return diagnostics


def build_summary(run_id: str, run_output_dir: Path, run_results_dir: Path, trace_path: Path, stage_copy: Path, state: RunState, status: str, failure_reason: str | None) -> dict[str, object]:
    final = final_sample(state)
    initial = state.step_samples[0] if state.step_samples else None
    final_window = build_final_window_diagnostics(state)
    summary = {
        "schema_version": "1.0",
        "run_id": run_id,
        "status": status,
        "failure_reason": failure_reason,
        "completed_steps": len(state.step_samples),
        "settlement_velocity_source": "omni.physics.tensors.RigidBodyView.get_velocities()",
        "physics_simulation_view_source": "isaacsim.core.simulation_manager.SimulationManager.get_physics_simulation_view()",
        "authoritative_runtime_velocity_source": "omni.physics.tensors.RigidBodyView.get_velocities()",
        "authoritative_runtime_pose_source": "omni.physics.tensors.RigidBodyView.get_transforms()",
        "sleep_state_source": "omni.physx.IPhysxSimulation.is_sleeping(stage_id, body_path)",
        "angular_speed_formula": "sqrt(wx**2 + wy**2 + wz**2)",
        "image_ref": "nvcr.io/nvidia/isaac-sim:6.0.1",
        "world": dict(WORLD_METADATA),
        "simulation": dict(SIMULATION_SETTINGS),
        "stage": {
            "canonical_usda": str(SCENE_USDA),
            "canonical_usd": str(SCENE_USD),
            "run_output_dir": str(run_output_dir),
            "run_results_dir": str(run_results_dir),
            "snapshot_usda": str(stage_copy),
            "snapshot_usd": str(run_output_dir / "physics_scene.usd"),
        },
        "completion": {
            "cube_contacted_ground": state.first_contact_step["cube"] is not None,
            "sphere_contacted_ground": state.first_contact_step["sphere"] is not None,
            "sphere_rebound_detected": state.rebound_step is not None,
            "cube_settled": state.cube_settle_step is not None,
            "sphere_settled": state.sphere_settle_step is not None,
            "unmet_conditions": build_unmet_conditions(state),
        },
        "contact_counts": state.contact_counts,
        "event_steps": {
            "cube_first_contact_step": state.first_contact_step["cube"],
            "sphere_first_contact_step": state.first_contact_step["sphere"],
            "sphere_rebound_step": state.rebound_step,
            "sphere_rebound_height_m": round(state.rebound_height_m, 6) if state.rebound_height_m is not None else None,
            "cube_settle_step": state.cube_settle_step,
            "sphere_settle_step": state.sphere_settle_step,
            "run_settle_step": state.run_settle_step,
            "cube_first_sleep_step": state.first_sleep_step["cube"],
            "sphere_first_sleep_step": state.first_sleep_step["sphere"],
            "cube_wake_step": state.wake_step["cube"],
            "sphere_wake_step": state.wake_step["sphere"],
        },
        "settle_counters": {
            "cube": {
                "final": state.post_contact_counters["cube"],
                "max": state.max_post_contact_counters["cube"],
            },
            "sphere": {
                "final": state.post_contact_counters["sphere"],
                "max": state.max_post_contact_counters["sphere"],
            },
        },
        "final_state": {
            "cube": sample_to_body_payload(final, "cube"),
            "sphere": sample_to_body_payload(final, "sphere"),
        },
        "state_sources": {
            "usd_sampled": {
                "pose": "UsdGeom.Xformable translation ops and rigid-body authored attrs (diagnostic only)",
                "linear_velocity": "UsdPhysics.RigidBodyAPI.GetVelocityAttr()",
                "angular_velocity": "UsdPhysics.RigidBodyAPI.GetAngularVelocityAttr()",
            },
            "runtime": {
                "physics_simulation_view": "isaacsim.core.simulation_manager.SimulationManager.get_physics_simulation_view()",
                "pose": "omni.physics.tensors.RigidBodyView.get_transforms()",
                "linear_velocity": "omni.physics.tensors.RigidBodyView.get_velocities()",
                "angular_velocity": "omni.physics.tensors.RigidBodyView.get_velocities()",
                "sleep": "omni.physx.IPhysxSimulation.is_sleeping(stage_id, body_path)",
            },
            "pose_velocity": "finite difference of runtime world positions across completed steps",
        },
        "initial_energy": {
            "cube": sample_to_body_payload(initial, "cube"),
            "sphere": sample_to_body_payload(initial, "sphere"),
        },
        "final_energy": {
            "cube": sample_to_body_payload(final, "cube"),
            "sphere": sample_to_body_payload(final, "sphere"),
        },
        "final_30_step_ranges": final_window,
        "cross_source_discrepancy_flags": final_window["discrepancy_flags"],
        "contact_events": state.contact_events,
        "thresholds": {
            "final_position_m": 0.001,
            "final_velocity_mps": 0.001,
            "rebound_height_m": 0.005,
            "settle_step": 1,
            "contact_step": 1,
        },
        "artifact_hashes": {
            "trace_csv": sha256_file(trace_path),
            "snapshot_usda": sha256_file(stage_copy),
            "snapshot_usd": sha256_file(run_output_dir / "physics_scene.usd"),
        },
        "pass_fail": "pass" if status == "passed" else "fail",
    }
    return summary


def copy_if_different(source: Path, target: Path) -> None:
    if source.resolve() == target.resolve():
        return
    shutil.copy2(source, target)


def run_single(UsdGeom, omni, app, run_id: str) -> dict[str, object]:
    from pxr import UsdPhysics
    from omni.physx import get_physx_simulation_interface

    run_output_dir, run_results_dir = ensure_run_dirs(run_id)
    stage_snapshot = run_output_dir / "physics_scene.usda"
    stage_snapshot_binary = run_output_dir / "physics_scene.usd"
    copy_if_different(SCENE_USDA, stage_snapshot)
    copy_if_different(SCENE_USD, stage_snapshot_binary)

    context = omni.usd.get_context()
    if not context.open_stage(str(SCENE_USDA)):
        fail(f"failed to open canonical stage for {run_id}")
    stage = context.get_stage()
    if stage is None:
        fail(f"missing stage after opening canonical scene for {run_id}")

    cube_prim = stage.GetPrimAtPath(BODY_SPECS["cube"]["path"])
    sphere_prim = stage.GetPrimAtPath(BODY_SPECS["sphere"]["path"])
    if not cube_prim or not cube_prim.IsValid():
        fail("missing cube prim")
    if not sphere_prim or not sphere_prim.IsValid():
        fail("missing sphere prim")

    cube_api = UsdPhysics.RigidBodyAPI(cube_prim)
    sphere_api = UsdPhysics.RigidBodyAPI(sphere_prim)

    state = init_run_state(run_id, run_output_dir, run_results_dir)
    current_step = {"value": 0}
    failure_reason: str | None = None
    status = "failed"
    trace_path = run_results_dir / "step_metrics.csv"

    def on_contact_report(contact_headers, contact_data):
        for header in contact_headers:
            diagnostic_reasons = record_contact_event(state, current_step["value"], header, contact_data)
            if diagnostic_reasons:
                pending_reasons.extend(diagnostic_reasons)

    pending_reasons: list[str] = []
    subscription = get_physx_simulation_interface().subscribe_contact_report_events(on_contact_report)
    timeline = omni.timeline.get_timeline_interface()
    timeline.play()
    runtime = create_runtime_sampler(
        stage,
        BODY_SPECS["cube"]["path"],
        BODY_SPECS["sphere"]["path"],
    )
    print(f"PHYSICS: {run_id} runtime velocity API = {runtime.velocity_api}", flush=True)
    print(f"PHYSICS: {run_id} runtime pose API = {runtime.pose_api}", flush=True)
    print(f"PHYSICS: {run_id} sleep API = {runtime.sleep_api}", flush=True)
    print(
        f"PHYSICS: {run_id} state policy = live runtime transform/velocity for decisions; authored USD velocity remains diagnostic only",
        flush=True,
    )

    print(f"PHYSICS: {run_id} started", flush=True)
    try:
        for step_index in range(1, MAX_STEPS + 1):
            # Loop order:
            # 1. advance one fixed physics step
            # 2. allow the physics state to update
            # 3. read transforms and velocities for the completed step
            # 4. process contact, rebound, and sleep state for that step
            # 5. update settling counters
            # 6. append the completed-step sample for later trace finalization
            previous_cube_counter = state.post_contact_counters["cube"]
            previous_sphere_counter = state.post_contact_counters["sphere"]
            current_step["value"] = step_index
            app.update()
            sample = capture_step_sample(UsdGeom, cube_prim, sphere_prim, cube_api, sphere_api, runtime, state, step_index)

            reasons: list[str] = []
            if step_index == 1 or step_index % 60 == 0 or step_index == MAX_STEPS:
                reasons.append("periodic")
            if pending_reasons:
                reasons.extend(pending_reasons)
                pending_reasons.clear()
            if previous_cube_counter > 0 and sample.cube_settle_counter == 0:
                reasons.append("cube_settle_reset")
            if previous_sphere_counter > 0 and sample.sphere_settle_counter == 0:
                reasons.append("sphere_settle_reset")
            if sample.sphere_rebounded and not state.rebound_announced:
                reasons.append("rebound")
                state.rebound_announced = True
            emit_diagnostic_line(run_id, sample, reasons)

            if sample.run_settled:
                break

        if not state.run_settled:
            failure_reason = f"{run_id} did not settle within {MAX_STEPS} steps"
            raise RuntimeError(failure_reason)

        status = "passed"
    except Exception as exc:
        if failure_reason is None:
            failure_reason = str(exc)
        raise
    finally:
        timeline.stop()
        try:
            subscription.unsubscribe()
        except Exception:
            pass

        trace_path = save_trace(run_results_dir, run_id, state)
        summary = build_summary(run_id, run_output_dir, run_results_dir, trace_path, stage_snapshot, state, status, failure_reason)
        write_json(run_results_dir / "summary.json", summary)
        if status == "passed":
            print(f"PHYSICS: {run_id} complete", flush=True)
        else:
            print(f"PHYSICS: {run_id} diagnostics persisted", flush=True)
    return summary


def parse_args(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Run the Phase 6 physics experiment.")
    parser.add_argument("--run", choices=RUN_IDS, help="Run only the selected simulation run.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    exit_code = 0
    app = SimulationApp(APP_CONFIG)
    print("PHYSICS: SimulationApp initialized", flush=True)

    try:
        import omni.timeline
        import omni.usd
        from pxr import UsdGeom

        if not SCENE_USDA.is_file():
            fail(f"missing canonical scene file: {SCENE_USDA}")
        if not SCENE_USD.is_file():
            fail(f"missing canonical scene file: {SCENE_USD}")

        run_ids = (args.run,) if args.run else RUN_IDS
        for run_id in run_ids:
            run_single(UsdGeom, omni, app, run_id)
        print("PHYSICS: selected runs completed", flush=True)
    except Exception:
        exit_code = 1
        traceback.print_exc()

    print("PHYSICS: requesting immediate shutdown", flush=True)
    app.close(skip_cleanup=True, exit_code=exit_code)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
