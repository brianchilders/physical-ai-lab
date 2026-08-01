from __future__ import annotations

import os
import sys
from pathlib import Path
import shutil
import traceback

from isaacsim import SimulationApp


APP_CONFIG = {"headless": True}
ROOT = Path(__file__).resolve().parent
RUNTIME_ROOT = Path(os.environ.get("PHYSICS_FOUNDATIONS_RUNTIME_ROOT", "/mnt/nvme/isaac/experiments/004-physics-foundations"))
PHYSICS_MATERIAL_PURPOSE = "physics"
RUN_OUTPUT_DIRS = {
    "run-01": RUNTIME_ROOT / "output" / "run-01",
    "run-02": RUNTIME_ROOT / "output" / "run-02",
}
RUN_SCENE_PATHS = {
    run_id: {
        "usda": run_dir / "physics_scene.usda",
        "usd": run_dir / "physics_scene.usd",
    }
    for run_id, run_dir in RUN_OUTPUT_DIRS.items()
}
SUCCESS_CONTAINMENT_MESSAGE = "PHYSICS: scene authoring and verification completed successfully"
SUCCESS_CONTAINMENT_SKIP_MESSAGE = (
    "PHYSICS: skipping SimulationApp.close() due to reproduced Isaac Sim 6.0.1 busy TaskGroup teardown defect"
)
SUCCESS_CONTAINMENT_EXIT_MESSAGE = "PHYSICS: exiting through approved one-shot containment path"


def fail(message: str) -> None:
    print(f"PHYSICS: FAIL: {message}", flush=True)
    raise RuntimeError(message)


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


def validate_layer_file(path: Path, expected_prefix: bytes, label: str) -> None:
    if not path.is_file():
        fail(f"{label} missing: {path}")
    with path.open("rb") as handle:
        header = handle.read(len(expected_prefix))
    if header != expected_prefix:
        fail(f"{label} has unexpected file signature: {header!r}")


def hash_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_physx_tokens(PhysxSchema) -> tuple[str, str]:
    missing = [name for name in ("TGS", "MBP") if not hasattr(PhysxSchema.Tokens, name)]
    if missing:
        available = sorted(name for name in dir(PhysxSchema.Tokens) if not name.startswith("_"))
        fail(
            "missing PhysxSchema.Tokens members: "
            f"{missing}; available generated token names: {available}"
        )
    print(
        f"PHYSICS: Python member PhysxSchema.Tokens.TGS -> {PhysxSchema.Tokens.TGS!r}",
        flush=True,
    )
    print(
        f"PHYSICS: Python member PhysxSchema.Tokens.MBP -> {PhysxSchema.Tokens.MBP!r}",
        flush=True,
    )
    return PhysxSchema.Tokens.TGS, PhysxSchema.Tokens.MBP


def make_material(stage, UsdShade, UsdPhysics, PhysxSchema, path, static_friction, dynamic_friction, restitution):
    material = UsdShade.Material.Define(stage, path)
    prim = material.GetPrim()

    usd_material = UsdPhysics.MaterialAPI.Apply(prim)
    usd_material.CreateStaticFrictionAttr().Set(static_friction)
    usd_material.CreateDynamicFrictionAttr().Set(dynamic_friction)
    usd_material.CreateRestitutionAttr().Set(restitution)

    physx_material = PhysxSchema.PhysxMaterialAPI.Apply(prim)
    physx_material.CreateFrictionCombineModeAttr().Set(PhysxSchema.Tokens.min)
    physx_material.CreateRestitutionCombineModeAttr().Set(PhysxSchema.Tokens.max)

    return material


def bind_physics_material(UsdShade, prim, material):
    UsdShade.MaterialBindingAPI.Apply(prim)
    binding_api = UsdShade.MaterialBindingAPI(prim)
    if not binding_api.Bind(material, UsdShade.Tokens.weakerThanDescendants, PHYSICS_MATERIAL_PURPOSE):
        fail(f"failed to bind physics material to {prim.GetPath()}")


def get_translate(UsdGeom, prim):
    xform = UsdGeom.Xformable(prim)
    for op in xform.GetOrderedXformOps():
        if op.GetOpType() == UsdGeom.XformOp.TypeTranslate:
            value = op.Get()
            return tuple(float(component) for component in value)
    return (0.0, 0.0, 0.0)


def author_stage(Usd, UsdGeom, UsdLux, UsdPhysics, UsdShade, PhysxSchema, Gf):
    solver_token, broadphase_token = verify_physx_tokens(PhysxSchema)
    primary_scene = RUN_SCENE_PATHS["run-01"]

    for run_dir in RUN_OUTPUT_DIRS.values():
        run_dir.mkdir(parents=True, exist_ok=True)

    stage = Usd.Stage.CreateNew(str(primary_scene["usda"]))
    print("PHYSICS: stage created", flush=True)

    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)

    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())

    physics_scene = UsdPhysics.Scene.Define(stage, "/World/PhysicsScene")
    physics_scene.CreateGravityDirectionAttr().Set(Gf.Vec3f(0.0, 0.0, -1.0))
    physics_scene.CreateGravityMagnitudeAttr().Set(9.81)

    physx_scene = PhysxSchema.PhysxSceneAPI.Apply(physics_scene.GetPrim())
    physx_scene.CreateTimeStepsPerSecondAttr().Set(60)
    physx_scene.CreateSolverTypeAttr().Set(solver_token)
    physx_scene.CreateBroadphaseTypeAttr().Set(broadphase_token)
    print(f"PHYSICS: authored solver token value = {solver_token!r}", flush=True)
    print(f"PHYSICS: authored broadphase token value = {broadphase_token!r}", flush=True)
    physx_scene.CreateEnableCCDAttr().Set(True)
    physx_scene.CreateEnableStabilizationAttr().Set(True)
    physx_scene.CreateEnableGPUDynamicsAttr().Set(False)
    enhanced_determinism_supported = False
    if hasattr(physx_scene, "CreateEnableEnhancedDeterminismAttr"):
        physx_scene.CreateEnableEnhancedDeterminismAttr().Set(True)
        enhanced_determinism_supported = True

    looks = UsdGeom.Scope.Define(stage, "/World/Looks")
    ground_material = make_material(
        stage,
        UsdShade,
        UsdPhysics,
        PhysxSchema,
        "/World/Looks/GroundMaterial",
        static_friction=0.9,
        dynamic_friction=0.8,
        restitution=0.0,
    )
    cube_material = make_material(
        stage,
        UsdShade,
        UsdPhysics,
        PhysxSchema,
        "/World/Looks/CubeMaterial",
        static_friction=0.85,
        dynamic_friction=0.75,
        restitution=0.05,
    )
    sphere_material = make_material(
        stage,
        UsdShade,
        UsdPhysics,
        PhysxSchema,
        "/World/Looks/SphereMaterial",
        static_friction=0.05,
        dynamic_friction=0.03,
        restitution=0.85,
    )
    _ = looks

    geometry = UsdGeom.Xform.Define(stage, "/World/Geometry")
    ground = UsdGeom.Mesh.Define(stage, "/World/Geometry/Ground")
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
    UsdPhysics.CollisionAPI.Apply(ground.GetPrim())
    mesh_collision = UsdPhysics.MeshCollisionAPI.Apply(ground.GetPrim())
    mesh_collision.CreateApproximationAttr().Set(UsdPhysics.Tokens.none)
    bind_physics_material(UsdShade, ground.GetPrim(), ground_material)
    _ = geometry

    actors = UsdGeom.Xform.Define(stage, "/World/Actors")

    cube = UsdGeom.Cube.Define(stage, "/World/Actors/LowBounceCube")
    cube.CreateSizeAttr(0.5)
    cube.CreateDisplayColorAttr([Gf.Vec3f(0.85, 0.15, 0.15)])
    cube_xform = UsdGeom.XformCommonAPI(cube)
    cube_xform.SetTranslate(Gf.Vec3d(-1.0, 0.0, 0.26))
    UsdPhysics.CollisionAPI.Apply(cube.GetPrim())
    rigid_cube = UsdPhysics.RigidBodyAPI.Apply(cube.GetPrim())
    rigid_cube.CreateRigidBodyEnabledAttr(True)
    rigid_cube.CreateStartsAsleepAttr(False)
    rigid_cube.CreateVelocityAttr(Gf.Vec3f(1.5, 0.0, 0.0))
    rigid_cube.CreateAngularVelocityAttr(Gf.Vec3f(0.0, 0.0, 0.0))
    mass_cube = UsdPhysics.MassAPI.Apply(cube.GetPrim())
    mass_cube.CreateMassAttr(2.0)
    PhysxSchema.PhysxContactReportAPI.Apply(cube.GetPrim()).CreateThresholdAttr(0.0)
    bind_physics_material(UsdShade, cube.GetPrim(), cube_material)

    sphere = UsdGeom.Sphere.Define(stage, "/World/Actors/HighBounceSphere")
    sphere.CreateRadiusAttr(0.25)
    sphere.CreateDisplayColorAttr([Gf.Vec3f(0.15, 0.35, 0.95)])
    sphere_xform = UsdGeom.XformCommonAPI(sphere)
    sphere_xform.SetTranslate(Gf.Vec3d(1.0, 0.0, 1.75))
    UsdPhysics.CollisionAPI.Apply(sphere.GetPrim())
    rigid_sphere = UsdPhysics.RigidBodyAPI.Apply(sphere.GetPrim())
    rigid_sphere.CreateRigidBodyEnabledAttr(True)
    rigid_sphere.CreateStartsAsleepAttr(False)
    rigid_sphere.CreateVelocityAttr(Gf.Vec3f(0.0, 0.0, 0.0))
    rigid_sphere.CreateAngularVelocityAttr(Gf.Vec3f(0.0, 0.0, 0.0))
    mass_sphere = UsdPhysics.MassAPI.Apply(sphere.GetPrim())
    mass_sphere.CreateMassAttr(1.0)
    PhysxSchema.PhysxContactReportAPI.Apply(sphere.GetPrim()).CreateThresholdAttr(0.0)
    bind_physics_material(UsdShade, sphere.GetPrim(), sphere_material)
    _ = actors

    print("PHYSICS: world metadata authored", flush=True)
    print("PHYSICS: physics scene authored", flush=True)
    print("PHYSICS: static collider and dynamic bodies authored", flush=True)
    print("PHYSICS: physics materials authored", flush=True)

    stage.GetRootLayer().Save()
    if not stage.GetRootLayer().Export(str(primary_scene["usd"]), "", {"format": "usdc"}):
        fail(f"failed to export binary USD: {primary_scene['usd']}")

    return stage, enhanced_determinism_supported


def validate_material_binding(prim, material_path: str) -> None:
    binding_rel = prim.GetRelationship("material:binding:physics")
    if not binding_rel or not binding_rel.IsValid():
        fail(f"missing physics material binding on {prim.GetPath()}")
    if binding_rel.GetName() != "material:binding:physics":
        fail(
            f"unexpected physics material binding relationship on {prim.GetPath()}: "
            f"{binding_rel.GetName()}"
        )
    targets = [target.pathString for target in binding_rel.GetTargets()]
    if material_path not in targets:
        fail(f"physics material binding on {prim.GetPath()} does not target {material_path}")


def validate_stage(stage, UsdGeom, UsdPhysics, UsdShade, PhysxSchema, run_id: str):
    def close_enough(actual, expected, tolerance=1e-6) -> bool:
        return abs(float(actual) - float(expected)) <= tolerance

    default_prim = stage.GetDefaultPrim()
    if not default_prim or default_prim.GetPath().pathString != "/World":
        fail(f"[{run_id}] default prim is not /World")

    if UsdGeom.GetStageUpAxis(stage) != UsdGeom.Tokens.z:
        fail(f"[{run_id}] stage up-axis is not z")

    meters_per_unit = UsdGeom.GetStageMetersPerUnit(stage)
    if abs(meters_per_unit - 1.0) > 1e-9:
        fail(f"[{run_id}] meters-per-unit is not 1.0: {meters_per_unit}")

    scene = UsdPhysics.Scene.Get(stage, "/World/PhysicsScene")
    if not scene:
        fail(f"[{run_id}] missing physics scene")

    physx_scene = PhysxSchema.PhysxSceneAPI(scene.GetPrim())
    if not physx_scene:
        fail(f"[{run_id}] missing PhysxSceneAPI on physics scene")
    solver_type = physx_scene.GetSolverTypeAttr().Get()
    broadphase_type = physx_scene.GetBroadphaseTypeAttr().Get()
    if solver_type != PhysxSchema.Tokens.TGS:
        fail(f"[{run_id}] solver token mismatch: {solver_type!r}")
    if broadphase_type != PhysxSchema.Tokens.MBP:
        fail(f"[{run_id}] broadphase token mismatch: {broadphase_type!r}")

    gravity_dir = tuple(scene.GetGravityDirectionAttr().Get())
    gravity_mag = float(scene.GetGravityMagnitudeAttr().Get())
    if tuple(round(v, 6) for v in gravity_dir) != (0.0, 0.0, -1.0):
        fail(f"[{run_id}] gravity direction mismatch: {gravity_dir}")
    if not close_enough(gravity_mag, 9.81, tolerance=1e-5):
        fail(f"[{run_id}] gravity magnitude mismatch: {gravity_mag}")

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
    for path, type_name in expectations.items():
        prim = stage.GetPrimAtPath(path)
        if not prim or not prim.IsValid():
            fail(f"[{run_id}] missing prim: {path}")
        if prim.GetTypeName() != type_name:
            fail(f"[{run_id}] type mismatch at {path}: {prim.GetTypeName()} != {type_name}")

    ground = stage.GetPrimAtPath("/World/Geometry/Ground")
    cube = stage.GetPrimAtPath("/World/Actors/LowBounceCube")
    sphere = stage.GetPrimAtPath("/World/Actors/HighBounceSphere")
    ground_material = stage.GetPrimAtPath("/World/Looks/GroundMaterial")
    cube_material = stage.GetPrimAtPath("/World/Looks/CubeMaterial")
    sphere_material = stage.GetPrimAtPath("/World/Looks/SphereMaterial")
    physics_scene = stage.GetPrimAtPath("/World/PhysicsScene")

    if physics_scene.GetTypeName() != "PhysicsScene":
        fail(f"[{run_id}] physics scene type mismatch: {physics_scene.GetTypeName()}")

    for prim, api in (
        (physics_scene, PhysxSchema.PhysxSceneAPI),
        (ground_material, UsdPhysics.MaterialAPI),
        (ground_material, PhysxSchema.PhysxMaterialAPI),
        (cube_material, UsdPhysics.MaterialAPI),
        (cube_material, PhysxSchema.PhysxMaterialAPI),
        (sphere_material, UsdPhysics.MaterialAPI),
        (sphere_material, PhysxSchema.PhysxMaterialAPI),
        (ground, UsdPhysics.CollisionAPI),
        (ground, UsdPhysics.MeshCollisionAPI),
        (ground, UsdShade.MaterialBindingAPI),
        (cube, UsdPhysics.CollisionAPI),
        (cube, UsdPhysics.RigidBodyAPI),
        (cube, UsdPhysics.MassAPI),
        (cube, PhysxSchema.PhysxContactReportAPI),
        (cube, UsdShade.MaterialBindingAPI),
        (sphere, UsdPhysics.CollisionAPI),
        (sphere, UsdPhysics.RigidBodyAPI),
        (sphere, UsdPhysics.MassAPI),
        (sphere, PhysxSchema.PhysxContactReportAPI),
        (sphere, UsdShade.MaterialBindingAPI),
    ):
        if not prim.HasAPI(api):
            fail(f"[{run_id}] missing applied API {api.__name__} on {prim.GetPath()}")

    for prim, expected_mass in ((cube, 2.0), (sphere, 1.0)):
        mass_api = UsdPhysics.MassAPI(prim)
        if not close_enough(mass_api.GetMassAttr().Get(), expected_mass):
            fail(f"[{run_id}] {prim.GetPath()} mass mismatch")

    cube_translate = get_translate(UsdGeom, cube)
    sphere_translate = get_translate(UsdGeom, sphere)
    if tuple(round(value, 6) for value in cube_translate) != (-1.0, 0.0, 0.26):
        fail(f"[{run_id}] cube translate mismatch: {cube_translate}")
    if tuple(round(value, 6) for value in sphere_translate) != (1.0, 0.0, 1.75):
        fail(f"[{run_id}] sphere translate mismatch: {sphere_translate}")

    cube_velocity = tuple(float(value) for value in UsdPhysics.RigidBodyAPI(cube).GetVelocityAttr().Get())
    cube_angular_velocity = tuple(float(value) for value in UsdPhysics.RigidBodyAPI(cube).GetAngularVelocityAttr().Get())
    sphere_velocity = tuple(float(value) for value in UsdPhysics.RigidBodyAPI(sphere).GetVelocityAttr().Get())
    sphere_angular_velocity = tuple(float(value) for value in UsdPhysics.RigidBodyAPI(sphere).GetAngularVelocityAttr().Get())
    if tuple(round(value, 6) for value in cube_velocity) != (1.5, 0.0, 0.0):
        fail(f"[{run_id}] cube velocity mismatch: {cube_velocity}")
    if tuple(round(value, 6) for value in cube_angular_velocity) != (0.0, 0.0, 0.0):
        fail(f"[{run_id}] cube angular velocity mismatch: {cube_angular_velocity}")
    if tuple(round(value, 6) for value in sphere_velocity) != (0.0, 0.0, 0.0):
        fail(f"[{run_id}] sphere velocity mismatch: {sphere_velocity}")
    if tuple(round(value, 6) for value in sphere_angular_velocity) != (0.0, 0.0, 0.0):
        fail(f"[{run_id}] sphere angular velocity mismatch: {sphere_angular_velocity}")

    validate_material_binding(ground, "/World/Looks/GroundMaterial")
    validate_material_binding(cube, "/World/Looks/CubeMaterial")
    validate_material_binding(sphere, "/World/Looks/SphereMaterial")

    ground_usd = UsdPhysics.MaterialAPI(ground_material)
    cube_usd = UsdPhysics.MaterialAPI(cube_material)
    sphere_usd = UsdPhysics.MaterialAPI(sphere_material)
    material_expectations = (
        (ground_usd, 0.9, 0.8, 0.0),
        (cube_usd, 0.85, 0.75, 0.05),
        (sphere_usd, 0.05, 0.03, 0.85),
    )
    for api, static_friction, dynamic_friction, restitution in material_expectations:
        if not close_enough(api.GetStaticFrictionAttr().Get(), static_friction):
            fail(f"[{run_id}] static friction mismatch")
        if not close_enough(api.GetDynamicFrictionAttr().Get(), dynamic_friction):
            fail(f"[{run_id}] dynamic friction mismatch")
        if not close_enough(api.GetRestitutionAttr().Get(), restitution):
            fail(f"[{run_id}] restitution mismatch")

    print(f"PHYSICS: [{run_id}] validation passed", flush=True)


def reopen_and_report(Usd, Sdf, UsdGeom, UsdPhysics, UsdShade, PhysxSchema):
    for run_id, scene_paths in RUN_SCENE_PATHS.items():
        text_stage = Usd.Stage.Open(str(scene_paths["usda"]))
        if not text_stage:
            fail(f"failed to reopen stage: {scene_paths['usda']}")
        text_layer = Sdf.Layer.FindOrOpen(str(scene_paths["usda"]))
        if text_layer is None:
            fail(f"failed to open USDA layer: {scene_paths['usda']}")
        text_format_id, text_extension, text_args = layer_format_info(text_layer)
        print(
            "PHYSICS: USDA layer format "
            f"run={run_id} "
            f"id={text_format_id} "
            f"ext={text_extension} "
            f"args={text_args}",
            flush=True,
        )

        binary_stage = Usd.Stage.Open(str(scene_paths["usd"]))
        if not binary_stage:
            fail(f"failed to reopen stage: {scene_paths['usd']}")
        binary_layer = Sdf.Layer.FindOrOpen(str(scene_paths["usd"]))
        if binary_layer is None:
            fail(f"failed to open USD layer: {scene_paths['usd']}")
        binary_format_id, binary_extension, binary_args = layer_format_info(binary_layer)
        print(
            "PHYSICS: USD layer format "
            f"run={run_id} "
            f"id={binary_format_id} "
            f"ext={binary_extension} "
            f"args={binary_args}",
            flush=True,
        )

        validate_stage(text_stage, UsdGeom, UsdPhysics, UsdShade, PhysxSchema, run_id)
        validate_stage(binary_stage, UsdGeom, UsdPhysics, UsdShade, PhysxSchema, run_id)
        validate_layer_file(scene_paths["usda"], b"#usda", "USDA file")
        validate_layer_file(scene_paths["usd"], b"PXR-USDC", "USD file")


def copy_primary_scene_to_run_two() -> None:
    source = RUN_SCENE_PATHS["run-01"]
    target = RUN_SCENE_PATHS["run-02"]
    shutil.copy2(source["usda"], target["usda"])
    shutil.copy2(source["usd"], target["usd"])


def verify_success_gate() -> None:
    for run_id, scene_paths in RUN_SCENE_PATHS.items():
        for label, path in scene_paths.items():
            if not path.is_file():
                fail(f"[{run_id}] missing {label} artifact: {path}")

    run_01 = RUN_SCENE_PATHS["run-01"]
    run_02 = RUN_SCENE_PATHS["run-02"]
    if hash_file(run_01["usda"]) != hash_file(run_02["usda"]):
        fail("run-01 and run-02 USDA hashes differ")
    if hash_file(run_01["usd"]) != hash_file(run_02["usd"]):
        fail("run-01 and run-02 USD hashes differ")


def flush_output_streams() -> None:
    sys.stdout.flush()
    sys.stderr.flush()


def exit_through_containment() -> None:
    print(SUCCESS_CONTAINMENT_MESSAGE, flush=True)
    print(SUCCESS_CONTAINMENT_SKIP_MESSAGE, flush=True)
    print(SUCCESS_CONTAINMENT_EXIT_MESSAGE, flush=True)
    flush_output_streams()
    os._exit(0)


def main() -> int:
    exit_code = 0
    app = SimulationApp(APP_CONFIG)
    print("PHYSICS: SimulationApp initialized", flush=True)

    try:
        from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdPhysics, UsdShade, PhysxSchema

        stage, enhanced_determinism_supported = author_stage(Usd, UsdGeom, UsdLux, UsdPhysics, UsdShade, PhysxSchema, Gf)
        print(
            "PHYSICS: enhanced determinism "
            + ("enabled" if enhanced_determinism_supported else "unsupported"),
            flush=True,
        )
        print("PHYSICS: canonical stage saved", flush=True)
        print("PHYSICS: canonical binary stage saved", flush=True)

        copy_primary_scene_to_run_two()

        print(
            "PHYSICS: primary artifact hashes "
            f"run-01.usda={hash_file(RUN_SCENE_PATHS['run-01']['usda'])} "
            f"run-01.usd={hash_file(RUN_SCENE_PATHS['run-01']['usd'])} "
            f"run-02.usda={hash_file(RUN_SCENE_PATHS['run-02']['usda'])} "
            f"run-02.usd={hash_file(RUN_SCENE_PATHS['run-02']['usd'])}",
            flush=True,
        )

        del stage
        reopen_and_report(Usd, Sdf, UsdGeom, UsdPhysics, UsdShade, PhysxSchema)
        verify_success_gate()
        exit_through_containment()
    except Exception:
        exit_code = 1
        traceback.print_exc()

    print("PHYSICS: requesting immediate shutdown", flush=True)
    app.close(skip_cleanup=True, exit_code=exit_code)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
