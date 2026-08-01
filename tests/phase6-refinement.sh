#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/.." && pwd)"

# shellcheck disable=SC1091
source "$repo_root/scripts/lib/env.sh"
# shellcheck disable=SC1091
source "$repo_root/scripts/lib/physics-foundations.sh"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

check_python_file_contains() {
  local pattern="$1"
  local file="$2"

  grep -n -E -e "$pattern" "$file" >/dev/null 2>&1 || fail "missing pattern '$pattern' in $file"
}

check_containment_order() {
  local file="$1"

  python3 - "$file" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text()
success_gate = text.find('verify_success_gate()')
flush_call = text.find('flush_output_streams()')
exit_call = text.find('os._exit(0)')
if success_gate == -1:
    raise SystemExit('missing verify_success_gate() call')
if flush_call == -1:
    raise SystemExit('missing flush_output_streams() call')
if exit_call == -1:
    raise SystemExit('missing os._exit(0) call')
if not (success_gate < flush_call < exit_call):
    raise SystemExit('containment ordering is invalid')
for needle in (
    'PHYSICS: scene authoring and verification completed successfully',
    'PHYSICS: skipping SimulationApp.close() due to reproduced Isaac Sim 6.0.1 busy TaskGroup teardown defect',
    'PHYSICS: exiting through approved one-shot containment path',
):
    if needle not in text:
        raise SystemExit(f'missing containment message: {needle}')
PY
}

check_inspector_initialization_order() {
  local file="$1"

  python3 - "$file" <<'PY'
from __future__ import annotations

import ast
from pathlib import Path
import sys

path = Path(sys.argv[1])
module = ast.parse(path.read_text())

simulation_app_import_line = None
simulation_app_assignment_line = None
first_pxr_import_line = None

for node in module.body:
    if isinstance(node, ast.ImportFrom) and node.module == 'isaacsim':
        for alias in node.names:
            if alias.name == 'SimulationApp':
                simulation_app_import_line = node.lineno
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == 'simulation_app':
                if isinstance(node.value, ast.Call) and getattr(node.value.func, 'id', None) == 'SimulationApp':
                    simulation_app_assignment_line = node.lineno
    if isinstance(node, ast.ImportFrom) and node.module == 'pxr' and first_pxr_import_line is None:
        first_pxr_import_line = node.lineno

if simulation_app_import_line is None:
    raise SystemExit('missing top-level SimulationApp import')
if simulation_app_assignment_line is None:
    raise SystemExit('missing top-level SimulationApp initialization')
if first_pxr_import_line is None:
    raise SystemExit('missing top-level pxr import')
if not (simulation_app_import_line < simulation_app_assignment_line < first_pxr_import_line):
    raise SystemExit('SimulationApp is not initialized before pxr imports')

text = path.read_text()
for needle in (
    'PHYSICS_INSPECT: SimulationApp initialized',
    'PHYSICS_INSPECT: pxr runtime imports loaded',
    'validate_stage_metadata',
    'validate_file_inventory',
    'validate_trace_continuity',
    'validate_contact_and_rebound',
    'validate_sleep_state',
    'validate_energy',
    'results/summary.md',
    'Usd.Stage.Open',
):
    if needle not in text:
        raise SystemExit(f'missing inspector marker or validation needle: {needle}')
forbidden = (
    '.Save(',
    '.Export(',
    'Flatten(',
)
for needle in forbidden:
    if needle in text:
        raise SystemExit(f'forbidden USD write operation present: {needle}')

if 'os._exit(0)' not in text:
    raise SystemExit('missing success-only os._exit(0) containment')
if 'exit_code = 1' not in text:
    raise SystemExit('missing nonzero failure exit path')
if 'traceback.print_exc()' not in text:
    raise SystemExit('missing traceback reporting on failure')
if 'flush_output_streams()' not in text:
    raise SystemExit('missing stdout/stderr flush helper')
PY
}

check_inspector_settling_fields() {
  local file="$1"

  python3 - "$file" <<'PY'
from __future__ import annotations

import ast
from pathlib import Path
import sys

path = Path(sys.argv[1])
module = ast.parse(path.read_text())

validate_settling = next(
    node for node in module.body
    if isinstance(node, ast.FunctionDef) and node.name == 'validate_settling'
)

subscript_keys: set[str] = set()
for node in ast.walk(validate_settling):
    if isinstance(node, ast.Subscript):
        value = node.value
        slice_node = node.slice
        if isinstance(value, ast.Name) and value.id == 'sphere_row' and isinstance(slice_node, ast.Constant) and isinstance(slice_node.value, str):
            subscript_keys.add(slice_node.value)
        if isinstance(value, ast.Name) and value.id == 'cube_row' and isinstance(slice_node, ast.Constant) and isinstance(slice_node.value, str):
            subscript_keys.add(slice_node.value)

required = {
    'sphere_runtime_total_speed_mps': 'runtime_total_speed_mps',
    'cube_runtime_planar_speed_mps': 'runtime_planar_speed_mps',
    'cube_runtime_angular_speed_rad_s': 'runtime_angular_speed_rad_s',
}
for label, needle in required.items():
    if needle not in subscript_keys:
        raise SystemExit(f'missing required settling field reference: {label}')

forbidden = 'runtime_speed_mps'
if forbidden in subscript_keys:
    raise SystemExit(f'forbidden settling field reference present: {forbidden}')

print('PASS: settling field references validated')
PY
}

check_inspector_final_window_metrics() {
  local file="$1"

  python3 - "$file" <<'PY'
from __future__ import annotations

import ast
from pathlib import Path
import sys

path = Path(sys.argv[1])
module = ast.parse(path.read_text())

def function(name: str) -> ast.FunctionDef:
    return next(
        node for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    )

def const_keys(node: ast.AST) -> set[str]:
    keys: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            keys.add(child.value)
    return keys

producer = function('validate_runtime_vectors_final')
producer_keys: set[str] = set()
for node in ast.walk(producer):
    if isinstance(node, ast.Assign):
        if len(node.targets) != 1:
            continue
        target = node.targets[0]
        if (
            isinstance(target, ast.Subscript)
            and isinstance(target.value, ast.Name)
            and target.value.id == 'final_window_summary'
            and isinstance(node.value, ast.Dict)
        ):
            producer_keys = {
                key.value
                for key in node.value.keys
                if isinstance(key, ast.Constant) and isinstance(key.value, str)
            }
            break

if not producer_keys:
    raise SystemExit('unable to extract producer final-window metric keys')

consumer = function('validate_final_window_ranges')
consumer_keys: set[str] = set()
for node in ast.walk(consumer):
    if isinstance(node, ast.For) and isinstance(node.target, ast.Name) and node.target.id == 'key':
        if isinstance(node.iter, ast.Tuple):
            consumer_keys.update(
                element.value
                for element in node.iter.elts
                if isinstance(element, ast.Constant) and isinstance(element.value, str)
            )

minimum_required = {
    'usd_sampled_planar_speed_mps',
    'runtime_planar_speed_mps',
    'runtime_total_speed_mps',
    'runtime_angular_speed_rad_s',
    'pose_speed_mps',
}
missing_from_producer = sorted((consumer_keys | minimum_required) - producer_keys)
if missing_from_producer:
    raise SystemExit(f'missing final-window metrics from producer: {missing_from_producer}')

missing_error_message = 'missing final window metric {key} for {actor} in {artifacts.run_id}'
if missing_error_message not in path.read_text():
    raise SystemExit('missing clear final-window metric error message template')

print('PASS: final-window metric sets validated')
PY
}

check_compare_full_trace_coverage() {
  local file="$1"

  python3 - "$file" <<'PY'
from __future__ import annotations

import ast
from pathlib import Path
import sys

path = Path(sys.argv[1])
module = ast.parse(path.read_text())
text = path.read_text()

required_strings = (
    'byte_level_equality',
    'semantic_equality',
    'expected_metadata_differences',
    'physics_bearing_differences',
    'unexplained_differences',
    'required_columns_missing',
    'TRACE_REQUIRED_COLUMNS',
    'TRACE_TOLERANCES',
    'artifact_hash_consistency',
    'comparison_overview',
)
for needle in required_strings:
    if needle not in text:
        raise SystemExit(f'missing comparison requirement: {needle}')

forbidden_strings = (
    'cube_runtime_kinetic_energy_j',
    'cube_runtime_potential_energy_j',
    'sphere_runtime_kinetic_energy_j',
    'sphere_runtime_potential_energy_j',
)
for needle in forbidden_strings:
    if needle in text:
        raise SystemExit(f'forbidden stale comparator field reference present: {needle}')

required_columns = {
    'runtime_total_speed_mps',
    'runtime_planar_speed_mps',
    'runtime_angular_speed_rad_s',
    'pose_speed_mps',
    'usd_sampled_planar_speed_mps',
}

trace_required_columns = next(
    node for node in module.body
    if isinstance(node, ast.Assign)
    and any(isinstance(target, ast.Name) and target.id == 'TRACE_REQUIRED_COLUMNS' for target in node.targets)
)
if not isinstance(trace_required_columns.value, ast.Tuple):
    raise SystemExit('TRACE_REQUIRED_COLUMNS is not a tuple literal')

present = {
    element.value
    for element in trace_required_columns.value.elts
    if isinstance(element, ast.Constant) and isinstance(element.value, str)
}
missing = sorted(required_columns - present)
if missing:
    raise SystemExit(f'missing required comparator trace columns: {missing}')

if 'field_statistics' not in text or 'first_divergence' not in text:
    raise SystemExit('missing full-trace statistics output')

print('PASS: comparator full-trace coverage validated')
PY
}

check_present() {
  local pattern="$1"
  local file="$2"

  grep -n -E -e "$pattern" "$file" >/dev/null 2>&1 || fail "missing pattern '$pattern' in $file"
}

check_not_present() {
  local pattern="$1"
  shift

  if grep -R -I -n -E -e "$pattern" "$@" >/dev/null 2>&1; then
    fail "found forbidden pattern: $pattern"
  fi
}

discover_shell_scripts() {
  (
    cd "$repo_root" && find . -type f -name '*.sh' -not -path './.git/*' | sort
  )
}

run_bash_syntax() {
  mapfile -t sh_files < <(discover_shell_scripts)
  bash -n "${sh_files[@]/#/$repo_root/}"
}

run_python_syntax() {
  python3 -m py_compile \
    "$repo_root/experiments/004-physics-foundations/physics_common.py" \
    "$repo_root/experiments/004-physics-foundations/create_physics_scene.py" \
    "$repo_root/experiments/004-physics-foundations/run_physics_experiment.py" \
    "$repo_root/experiments/004-physics-foundations/inspect_physics_results.py" \
    "$repo_root/experiments/004-physics-foundations/compare_physics_runs.py"
}

run_policy_checks() {
  local phase6_code_files=(
    "$repo_root/scripts/lib/physics-foundations.sh"
    "$repo_root/scripts/prepare-physics-foundations.sh"
    "$repo_root/scripts/prepare-physics-foundations-ownership.sh"
    "$repo_root/scripts/validate-physics-foundations-ownership.sh"
    "$repo_root/scripts/create-physics-scene.sh"
    "$repo_root/scripts/run-physics-experiment.sh"
    "$repo_root/scripts/inspect-physics-results.sh"
    "$repo_root/scripts/compare-physics-runs.sh"
    "$repo_root/Makefile"
  )
  local phase6_doc_files=(
    "$repo_root/experiments/004-physics-foundations/README.md"
    "$repo_root/experiments/004-physics-foundations/expected-results.md"
    "$repo_root/experiments/004-physics-foundations/expected-hierarchy.txt"
    "$repo_root/experiments/004-physics-foundations/results/summary.md"
  )

  check_not_present 'https?://|omniverse://|ngc://' "${phase6_code_files[@]}"
  check_not_present 'ros2|rclpy|ROS 2|ros-core' "${phase6_code_files[@]}"
  check_not_present 'Isaac Lab|isaaclab' "${phase6_code_files[@]}"
  check_not_present 'DGX Spark|dgx spark' "${phase6_code_files[@]}"
  check_not_present 'docker pull|--pull=always' \
    "$repo_root/scripts/create-physics-scene.sh" \
    "$repo_root/scripts/run-physics-experiment.sh" \
    "$repo_root/scripts/inspect-physics-results.sh" \
    "$repo_root/scripts/validate-physics-foundations-ownership.sh"
  check_not_present '--network=host' \
    "$repo_root/scripts/create-physics-scene.sh" \
    "$repo_root/scripts/run-physics-experiment.sh" \
    "$repo_root/scripts/inspect-physics-results.sh" \
    "$repo_root/scripts/validate-physics-foundations-ownership.sh" \
    "$repo_root/Makefile"

  check_present '--pull=never' "$repo_root/scripts/create-physics-scene.sh"
  check_present '--pull=never' "$repo_root/scripts/run-physics-experiment.sh"
  check_present '--pull=never' "$repo_root/scripts/inspect-physics-results.sh"
  check_present '--pull=never' "$repo_root/scripts/compare-physics-runs.sh"
  check_present '--pull=never' "$repo_root/scripts/validate-physics-foundations-ownership.sh"
  check_present '--user 1234:1234' "$repo_root/scripts/create-physics-scene.sh"
  check_present '--user 1234:1234' "$repo_root/scripts/run-physics-experiment.sh"
  check_present '--user 1234:1234' "$repo_root/scripts/inspect-physics-results.sh"
  check_present '--user 1234:1234' "$repo_root/scripts/validate-physics-foundations-ownership.sh"
  check_present ':/workspace:ro' "$repo_root/scripts/create-physics-scene.sh"
  check_present ':/mnt/nvme/isaac:rw' "$repo_root/scripts/create-physics-scene.sh"
  check_present ':/workspace:ro' "$repo_root/scripts/run-physics-experiment.sh"
  check_present ':/mnt/nvme/isaac:rw' "$repo_root/scripts/run-physics-experiment.sh"
  check_present ':/workspace:ro' "$repo_root/scripts/inspect-physics-results.sh"
  check_present ':/workspace:ro' "$repo_root/scripts/compare-physics-runs.sh"
  check_present 'PHYSICS_FOUNDATIONS_RUNTIME_ROOT' "$repo_root/scripts/run-physics-experiment.sh"
  check_present 'output:ro' "$repo_root/scripts/inspect-physics-results.sh"
  check_present 'results:rw' "$repo_root/scripts/inspect-physics-results.sh"
  check_present ':/mnt/nvme/isaac:rw' "$repo_root/scripts/compare-physics-runs.sh"
  check_present 'PHYSICS_FOUNDATIONS_RUNTIME_ROOT=/workspace/experiments/004-physics-foundations' "$repo_root/scripts/inspect-physics-results.sh"
  check_present 'PHYSICS_FOUNDATIONS_RUNTIME_ROOT=/mnt/nvme/isaac/experiments/004-physics-foundations' "$repo_root/scripts/compare-physics-runs.sh"
  check_present 'SimulationApp initialized' "$repo_root/experiments/004-physics-foundations/inspect_physics_results.py"
  check_present 'pxr runtime imports loaded' "$repo_root/experiments/004-physics-foundations/inspect_physics_results.py"
  check_not_present 'create_physics_scene.log' "$repo_root/scripts/create-physics-scene.sh"
  check_present 'ACCEPT_EULA=Y' "$repo_root/scripts/create-physics-scene.sh"
  check_present 'PRIVACY_CONSENT=N' "$repo_root/scripts/create-physics-scene.sh"
  check_present 'ACCEPT_EULA=Y' "$repo_root/scripts/run-physics-experiment.sh"
  check_present 'PRIVACY_CONSENT=N' "$repo_root/scripts/run-physics-experiment.sh"
  check_present 'ACCEPT_EULA=Y' "$repo_root/scripts/inspect-physics-results.sh"
  check_present 'PRIVACY_CONSENT=N' "$repo_root/scripts/inspect-physics-results.sh"

  check_present 'CONFIRM_CHOWN' "$repo_root/scripts/prepare-physics-foundations-ownership.sh"
  check_present '1234:1234' "$repo_root/scripts/prepare-physics-foundations-ownership.sh"
  check_present 'chown 1234:1234' "$repo_root/scripts/prepare-physics-foundations-ownership.sh"
  check_present '/output/run-01' "$repo_root/scripts/prepare-physics-foundations-ownership.sh"
  check_present '/output/run-02' "$repo_root/scripts/prepare-physics-foundations-ownership.sh"
  check_present '/results/run-01' "$repo_root/scripts/prepare-physics-foundations-ownership.sh"
  check_present '/results/run-02' "$repo_root/scripts/prepare-physics-foundations-ownership.sh"
  check_present '/output/run-01' "$repo_root/scripts/validate-physics-foundations-ownership.sh"
  check_present '/output/run-02' "$repo_root/scripts/validate-physics-foundations-ownership.sh"
  check_present '/results/run-01' "$repo_root/scripts/validate-physics-foundations-ownership.sh"
  check_present '/results/run-02' "$repo_root/scripts/validate-physics-foundations-ownership.sh"
  check_present 'stat -c "%u:%g"' "$repo_root/scripts/validate-physics-foundations-ownership.sh"
  check_present 'rm -f "\$probe"' "$repo_root/scripts/validate-physics-foundations-ownership.sh"
  check_present 'physics_foundations_runtime_root' "$repo_root/scripts/lib/physics-foundations.sh"
  check_present 'physics_foundations_output_dir' "$repo_root/scripts/lib/physics-foundations.sh"
  check_present 'physics_foundations_results_dir' "$repo_root/scripts/lib/physics-foundations.sh"
  check_present 'physics_foundations_ownership_dirs' "$repo_root/scripts/lib/physics-foundations.sh"

  check_present 'world metadata authored' "$repo_root/experiments/004-physics-foundations/create_physics_scene.py"
  check_present 'PhysxSceneAPI' "$repo_root/experiments/004-physics-foundations/create_physics_scene.py"
  check_present 'PhysxContactReportAPI' "$repo_root/experiments/004-physics-foundations/create_physics_scene.py"
  check_present 'RigidBodyAPI' "$repo_root/experiments/004-physics-foundations/create_physics_scene.py"
  check_present 'MassAPI' "$repo_root/experiments/004-physics-foundations/create_physics_scene.py"
  check_present 'MaterialAPI' "$repo_root/experiments/004-physics-foundations/create_physics_scene.py"
  check_present 'physics' "$repo_root/experiments/004-physics-foundations/create_physics_scene.py"
  check_present 'PhysxSchema.Tokens.TGS' "$repo_root/experiments/004-physics-foundations/create_physics_scene.py"
  check_present 'PhysxSchema.Tokens.MBP' "$repo_root/experiments/004-physics-foundations/create_physics_scene.py"
  check_not_present 'PhysxSchema\.Tokens\.tGS|PhysxSchema\.Tokens\.mBP' "$repo_root/experiments/004-physics-foundations/create_physics_scene.py"
  check_not_present 'Set\("TGS"\)|Set\("MBP"\)' "$repo_root/experiments/004-physics-foundations/create_physics_scene.py"
  check_present 'material:binding:physics' "$repo_root/experiments/004-physics-foundations/create_physics_scene.py"
  check_not_present 'UsdShade\.Tokens\.physics' "$repo_root/experiments/004-physics-foundations/create_physics_scene.py"
  check_present 'os._exit\(0\)' "$repo_root/experiments/004-physics-foundations/create_physics_scene.py"
  check_not_present 'os._exit' "$repo_root/experiments/004-physics-foundations/run_physics_experiment.py"
  check_present 'Destroying busy TaskGroup!' "$repo_root/experiments/004-physics-foundations/README.md"
  check_present 'Destroying busy TaskGroup!' "$repo_root/experiments/004-physics-foundations/expected-results.md"
  check_containment_order "$repo_root/experiments/004-physics-foundations/create_physics_scene.py"

  check_present 'cube_kinetic_energy_j' "$repo_root/experiments/004-physics-foundations/run_physics_experiment.py"
  check_present 'cube_potential_energy_j' "$repo_root/experiments/004-physics-foundations/run_physics_experiment.py"
  check_present 'cube_total_mechanical_energy_j' "$repo_root/experiments/004-physics-foundations/run_physics_experiment.py"
  check_present 'sphere_kinetic_energy_j' "$repo_root/experiments/004-physics-foundations/run_physics_experiment.py"
  check_present 'sphere_potential_energy_j' "$repo_root/experiments/004-physics-foundations/run_physics_experiment.py"
  check_present 'sphere_total_mechanical_energy_j' "$repo_root/experiments/004-physics-foundations/run_physics_experiment.py"
  check_present 'sphere_rebounded' "$repo_root/experiments/004-physics-foundations/run_physics_experiment.py"
  check_present 'cube_settle_step' "$repo_root/experiments/004-physics-foundations/run_physics_experiment.py"
  check_present 'sphere_settle_step' "$repo_root/experiments/004-physics-foundations/run_physics_experiment.py"
  check_present 'run_settle_step' "$repo_root/experiments/004-physics-foundations/run_physics_experiment.py"
  check_present 'thresholds' "$repo_root/experiments/004-physics-foundations/run_physics_experiment.py"
  check_present 'world' "$repo_root/experiments/004-physics-foundations/run_physics_experiment.py"
  check_present '--run' "$repo_root/experiments/004-physics-foundations/run_physics_experiment.py"
  check_present 'choices=RUN_IDS' "$repo_root/experiments/004-physics-foundations/run_physics_experiment.py"
  check_present 'failure_reason' "$repo_root/experiments/004-physics-foundations/run_physics_experiment.py"
  check_present 'completed_steps' "$repo_root/experiments/004-physics-foundations/run_physics_experiment.py"
  check_present 'diagnostics persisted' "$repo_root/experiments/004-physics-foundations/run_physics_experiment.py"
  check_present 'step_metrics.csv' "$repo_root/experiments/004-physics-foundations/run_physics_experiment.py"
  check_present 'summary.json' "$repo_root/experiments/004-physics-foundations/run_physics_experiment.py"
  check_present 'status = "failed"' "$repo_root/experiments/004-physics-foundations/run_physics_experiment.py"
  check_present 'Loop order:' "$repo_root/experiments/004-physics-foundations/run_physics_experiment.py"
  check_present 'usd_sampled_linear_velocity' "$repo_root/experiments/004-physics-foundations/run_physics_experiment.py"
  check_present 'runtime_linear_velocity' "$repo_root/experiments/004-physics-foundations/run_physics_experiment.py"
  check_present 'pose_linear_velocity' "$repo_root/experiments/004-physics-foundations/run_physics_experiment.py"
  check_present 'usd_sampled_vertical_velocity_mps' "$repo_root/experiments/004-physics-foundations/run_physics_experiment.py"
  check_present 'runtime_vertical_velocity_mps' "$repo_root/experiments/004-physics-foundations/run_physics_experiment.py"
  check_present 'pose_vertical_velocity_mps' "$repo_root/experiments/004-physics-foundations/run_physics_experiment.py"
  check_present 'cube_sleeping' "$repo_root/experiments/004-physics-foundations/run_physics_experiment.py"
  check_present 'sphere_sleeping' "$repo_root/experiments/004-physics-foundations/run_physics_experiment.py"
  check_present 'vector_magnitude\(angular_velocity\)' "$repo_root/experiments/004-physics-foundations/run_physics_experiment.py"
  check_not_present 'math\.radians\(|/ 60|timeStepsPerSecond' "$repo_root/experiments/004-physics-foundations/run_physics_experiment.py"
  check_not_present 'state\.settle_step' "$repo_root/experiments/004-physics-foundations/run_physics_experiment.py"

  python3 - "$repo_root" <<'PY'
from pathlib import Path
import sys

repo_root = Path(sys.argv[1])
path = repo_root / "experiments/004-physics-foundations/run_physics_experiment.py"
text = path.read_text()

capture = text.split('def capture_step_sample', 1)[1].split('def sample_contact_state', 1)[0]
required_in_capture = (
    'previous_vertical_velocity is not None and previous_vertical_velocity <= 0.0',
    'sphere_sample.runtime_vertical_speed > 0.0',
    'cube_sample.runtime_planar_speed <= 0.02',
    'cube_sample.runtime_angular_speed <= 0.05',
    'sphere_sample.runtime_speed <= 0.02',
    'state.cube_settle_step = step_index',
    'state.sphere_settle_step = step_index',
    'state.run_settle_step = step_index',
    'state.previous_runtime_vertical_velocity["cube"] = cube_sample.runtime_vertical_speed',
    'state.previous_runtime_vertical_velocity["sphere"] = sphere_sample.runtime_vertical_speed',
    'body_energy(BODY_SPECS["cube"], cube_sample.runtime_position, cube_sample.runtime_linear_velocity',
    'body_energy(BODY_SPECS["sphere"], sphere_sample.runtime_position, sphere_sample.runtime_linear_velocity',
)
for needle in required_in_capture:
    if needle not in capture:
        raise SystemExit(f"missing runtime-policy capture needle: {needle}")

forbidden_in_capture = (
    'cube_sample.sampled_planar_speed <= 0.02',
    'cube_sample.sampled_angular_speed <= 0.05',
    'sphere_sample.sampled_speed <= 0.02',
    'sphere_sample.sampled_linear_velocity[2] > 0.0',
    'state.settle_step = step_index',
)
for needle in forbidden_in_capture:
    if needle in capture:
        raise SystemExit(f"found stale settlement path: {needle}")

energy = text.split('def body_energy', 1)[1].split('def contact_name', 1)[0]
if 'rotational =' in energy:
    raise SystemExit('rotational kinetic energy is still authored in body_energy')
for needle in ('0.5 * mass * speed * speed', 'total = translational + potential', 'return translational, potential, total'):
    if needle not in energy:
        raise SystemExit(f"missing energy policy needle: {needle}")

if 'state_sources": {\n            "usd_sampled"' not in text:
    raise SystemExit('missing usd_sampled state_sources block')
if 'settlement_velocity_source": "omni.physics.tensors.RigidBodyView.get_velocities()"' not in text:
    raise SystemExit('missing runtime settlement source declaration')
print('PASS: runtime policy and energy source checks')
PY

  python3 - "$repo_root" <<'PY'
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

repo_root = Path(sys.argv[1])
module_path = repo_root / "experiments/004-physics-foundations/physics_common.py"
spec = spec_from_file_location("physics_common", module_path)
module = module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
value = module.vector_magnitude([3.0, 4.0, 0.0])
if abs(value - 5.0) > 1e-12:
    raise SystemExit(f'vector_magnitude validation failed: {value!r}')
print('PASS: vector_magnitude([3, 4, 0]) == 5')
PY

  python3 - "$repo_root" <<'PY'
from pathlib import Path
import sys

repo_root = Path(sys.argv[1])
path = repo_root / "experiments/004-physics-foundations/inspect_physics_results.py"
text = path.read_text()

required = (
    'write_summary_report(report)',
    'report["stage"]["report_hash"] = sha256_file(report_path)',
    'report["stage"]["report_size"] = report_path.stat().st_size',
    'verify_success_gate(report, report_path)',
    'PHYSICS_INSPECT: root stage opened',
    'PHYSICS_INSPECT: run results opened',
    'PHYSICS_INSPECT: world metadata validated',
    'PHYSICS_INSPECT: hierarchy validated',
    'PHYSICS_INSPECT: inspection passed',
    'PHYSICS_INSPECT: summary report written to',
    'PHYSICS_INSPECT: formal inspection completed successfully',
    'PHYSICS_INSPECT: skipping SimulationApp.close() due to reproduced Isaac Sim 6.0.1 busy TaskGroup teardown defect',
    'PHYSICS_INSPECT: terminating one-shot inspector',
    'sys.stdout.flush()',
    'sys.stderr.flush()',
    'os._exit(0)',
    'traceback.print_exc()',
    'exit_code = 1',
    'handle.flush()',
    'os.fsync(handle.fileno())',
)
positions = {}
for needle in required:
    position = text.find(needle)
    if position == -1:
        raise SystemExit(f'missing success containment needle: {needle}')
    positions[needle] = position

ordered = (
    'write_summary_report(report)',
    'report["stage"]["report_hash"] = sha256_file(report_path)',
    'report["stage"]["report_size"] = report_path.stat().st_size',
    'verify_success_gate(report, report_path)',
)
for earlier, later in zip(ordered, ordered[1:]):
    if not (positions[earlier] < positions[later]):
        raise SystemExit(f'invalid success containment order: {earlier} !< {later}')

success_segment = text.split('verify_success_gate(report, report_path)', 1)[1]
success_order = (
    'PHYSICS_INSPECT: root stage opened',
    'PHYSICS_INSPECT: run results opened',
    'PHYSICS_INSPECT: world metadata validated',
    'PHYSICS_INSPECT: hierarchy validated',
    'PHYSICS_INSPECT: inspection passed',
    'PHYSICS_INSPECT: summary report written to',
    'PHYSICS_INSPECT: formal inspection completed successfully',
    'PHYSICS_INSPECT: skipping SimulationApp.close() due to reproduced Isaac Sim 6.0.1 busy TaskGroup teardown defect',
    'PHYSICS_INSPECT: terminating one-shot inspector',
    'flush_output_streams()',
    'os._exit(0)',
)
success_positions = {}
for needle in success_order:
    position = success_segment.find(needle)
    if position == -1:
        raise SystemExit(f'missing success-path needle: {needle}')
    success_positions[needle] = position

for earlier, later in zip(success_order, success_order[1:]):
    if not (success_positions[earlier] < success_positions[later]):
        raise SystemExit(f'invalid success containment order: {earlier} !< {later}')
print('PASS: inspector success containment validated')
PY

  check_present 'os._exit\(0\)' "$repo_root/experiments/004-physics-foundations/inspect_physics_results.py"
  check_present 'validate_file_inventory' "$repo_root/experiments/004-physics-foundations/inspect_physics_results.py"
  check_present 'validate_stage_metadata' "$repo_root/experiments/004-physics-foundations/inspect_physics_results.py"
  check_present 'validate_trace_continuity' "$repo_root/experiments/004-physics-foundations/inspect_physics_results.py"
  check_present 'validate_runtime_vectors_final' "$repo_root/experiments/004-physics-foundations/inspect_physics_results.py"
  check_present 'validate_contact_and_rebound' "$repo_root/experiments/004-physics-foundations/inspect_physics_results.py"
  check_present 'validate_sleep_state' "$repo_root/experiments/004-physics-foundations/inspect_physics_results.py"
  check_present 'validate_energy' "$repo_root/experiments/004-physics-foundations/inspect_physics_results.py"
  check_present 'write_summary_report' "$repo_root/experiments/004-physics-foundations/inspect_physics_results.py"
  check_present 'results/summary.md' "$repo_root/experiments/004-physics-foundations/inspect_physics_results.py"
  check_present 'PhysX runtime state drives settlement' "$repo_root/experiments/004-physics-foundations/inspect_physics_results.py"
  check_present 'contact_unknown records are repeated callback payloads' "$repo_root/experiments/004-physics-foundations/inspect_physics_results.py"
  check_present 'Step 0 contact evidence exists only in the summary contact event stream' "$repo_root/experiments/004-physics-foundations/inspect_physics_results.py"
  check_present 'inspection cross-checks the summary and trace' "$repo_root/experiments/004-physics-foundations/inspect_physics_results.py"
  check_present 'runtime_total_mechanical_energy_j' "$repo_root/experiments/004-physics-foundations/inspect_physics_results.py"
  check_present 'usd_sampled_kinetic_energy_j' "$repo_root/experiments/004-physics-foundations/inspect_physics_results.py"
  check_present 'world metadata validated' "$repo_root/experiments/004-physics-foundations/inspect_physics_results.py"
  check_present 'formal inspection completed successfully' "$repo_root/experiments/004-physics-foundations/inspect_physics_results.py"
  check_present 'skipping SimulationApp.close\(\) due to reproduced Isaac Sim 6.0.1 busy TaskGroup teardown defect' "$repo_root/experiments/004-physics-foundations/inspect_physics_results.py"
  check_present 'terminating one-shot inspector' "$repo_root/experiments/004-physics-foundations/inspect_physics_results.py"
  check_present 'sys\.stdout\.flush\(\)' "$repo_root/experiments/004-physics-foundations/inspect_physics_results.py"
  check_present 'sys\.stderr\.flush\(\)' "$repo_root/experiments/004-physics-foundations/inspect_physics_results.py"
  check_inspector_initialization_order "$repo_root/experiments/004-physics-foundations/inspect_physics_results.py"
  check_inspector_settling_fields "$repo_root/experiments/004-physics-foundations/inspect_physics_results.py"
  check_inspector_final_window_metrics "$repo_root/experiments/004-physics-foundations/inspect_physics_results.py"

  check_present 'finalPositionMeters' "$repo_root/experiments/004-physics-foundations/compare_physics_runs.py"
  check_present 'finalVelocityMetersPerSecond' "$repo_root/experiments/004-physics-foundations/compare_physics_runs.py"
  check_present 'reboundHeightMeters' "$repo_root/experiments/004-physics-foundations/compare_physics_runs.py"
  check_present 'settleStep' "$repo_root/experiments/004-physics-foundations/compare_physics_runs.py"
  check_present 'contactStep' "$repo_root/experiments/004-physics-foundations/compare_physics_runs.py"
  check_present 'first_divergence' "$repo_root/experiments/004-physics-foundations/compare_physics_runs.py"
  check_compare_full_trace_coverage "$repo_root/experiments/004-physics-foundations/compare_physics_runs.py"

  check_present 'output/*' "$repo_root/experiments/004-physics-foundations/.gitignore"
  check_present 'results/*' "$repo_root/experiments/004-physics-foundations/.gitignore"
  check_present '__pycache__/' "$repo_root/experiments/004-physics-foundations/.gitignore"
  check_present '\*\.py\[cod\]' "$repo_root/experiments/004-physics-foundations/.gitignore"
  check_present '\*.usd' "$repo_root/experiments/004-physics-foundations/.gitignore"
  check_present '\*.usda' "$repo_root/experiments/004-physics-foundations/.gitignore"
  check_present '\*.csv' "$repo_root/experiments/004-physics-foundations/.gitignore"
  check_present '\*.json' "$repo_root/experiments/004-physics-foundations/.gitignore"
  check_present '\*.log' "$repo_root/experiments/004-physics-foundations/.gitignore"

  check_present 'Physics Foundations' "$repo_root/experiments/004-physics-foundations/README.md"
  check_present 'create_physics_scene.py' "$repo_root/experiments/004-physics-foundations/README.md"
  check_present 'run_physics_experiment.py' "$repo_root/experiments/004-physics-foundations/README.md"
  check_present 'inspect_physics_results.py' "$repo_root/experiments/004-physics-foundations/README.md"
  check_present 'compare_physics_runs.py' "$repo_root/experiments/004-physics-foundations/README.md"
  check_present 'final position: `<= 1 mm`' "$repo_root/experiments/004-physics-foundations/expected-results.md"
  check_present 'kinetic energy' "$repo_root/experiments/004-physics-foundations/expected-results.md"
  check_present 'gravitational potential energy' "$repo_root/experiments/004-physics-foundations/expected-results.md"
  check_present 'total mechanical energy' "$repo_root/experiments/004-physics-foundations/expected-results.md"
  check_present '/World/Actors/LowBounceCube' "$repo_root/experiments/004-physics-foundations/expected-hierarchy.txt"
  check_present '/World/Actors/HighBounceSphere' "$repo_root/experiments/004-physics-foundations/expected-hierarchy.txt"
  check_present 'prepare-physics-foundations' "$repo_root/Makefile"
  check_present 'validate-physics-foundations-ownership' "$repo_root/Makefile"
  check_present 'create-physics-scene' "$repo_root/Makefile"
  check_present 'run-physics-experiment' "$repo_root/Makefile"
  check_present 'inspect-physics-results' "$repo_root/Makefile"
  check_present 'compare-physics-runs' "$repo_root/Makefile"
  check_present 'test-phase6' "$repo_root/Makefile"
}

main() {
  case "${1:-all}" in
    bash-syntax) run_bash_syntax ;;
    python-syntax) run_python_syntax ;;
    policy-check) run_policy_checks ;;
    all)
      run_bash_syntax
      run_python_syntax
      run_policy_checks
      ;;
    *)
      fail "unknown mode: ${1:-}"
      ;;
  esac
}

main "$@"
