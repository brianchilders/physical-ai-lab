#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/.." && pwd)"

# shellcheck disable=SC1091
source "$repo_root/scripts/lib/env.sh"
# shellcheck disable=SC1091
source "$repo_root/scripts/lib/openusd-foundations.sh"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
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
    "$repo_root/experiments/002-openusd-foundations/create_scene.py" \
    "$repo_root/experiments/002-openusd-foundations/inspect_scene.py"
}

check_not_present() {
  local pattern="$1"
  local files=("${@:2}")

  if grep -R -I -n -E -e "$pattern" "${files[@]}" >/dev/null 2>&1; then
    fail "Found forbidden pattern: $pattern"
  fi
}

check_present() {
  local pattern="$1"
  local file="$2"

  grep -n -E -e "$pattern" "$file" >/dev/null 2>&1 || \
    fail "Missing expected pattern '$pattern' in $file"
}

run_policy_checks() {
  local phase4_files=(
    "$repo_root/experiments/002-openusd-foundations"
    "$repo_root/scripts/run-openusd-foundations.sh"
    "$repo_root/scripts/inspect-openusd-foundations.sh"
    "$repo_root/scripts/prepare-openusd-foundations.sh"
    "$repo_root/scripts/prepare-openusd-foundations-ownership.sh"
    "$repo_root/scripts/validate-openusd-foundations-ownership.sh"
    "$repo_root/Makefile"
  )

  "$repo_root/tests/phase2-refinement.sh" policy-check >/dev/null 2>&1

  check_not_present 'https?://|omniverse://|ngc://' "${phase4_files[@]}"
  check_not_present 'ros2|rclpy|ROS 2|ros-core' "${phase4_files[@]}"
  check_not_present 'docker pull|--pull=always' \
    "$repo_root/scripts/run-openusd-foundations.sh" \
    "$repo_root/scripts/inspect-openusd-foundations.sh"
  check_not_present '--network=host' \
    "$repo_root/scripts/run-openusd-foundations.sh" \
    "$repo_root/scripts/inspect-openusd-foundations.sh" \
    "$repo_root/Makefile"

  check_present '--pull=never' "$repo_root/scripts/run-openusd-foundations.sh"
  check_present '--pull=never' "$repo_root/scripts/inspect-openusd-foundations.sh"
  check_present '--user 1234:1234' "$repo_root/scripts/run-openusd-foundations.sh"
  check_present '--user 1234:1234' "$repo_root/scripts/inspect-openusd-foundations.sh"
  check_present 'ACCEPT_EULA=Y' "$repo_root/scripts/run-openusd-foundations.sh"
  check_present 'PRIVACY_CONSENT=N' "$repo_root/scripts/run-openusd-foundations.sh"
  check_present 'ACCEPT_EULA=Y' "$repo_root/scripts/inspect-openusd-foundations.sh"
  check_present 'PRIVACY_CONSENT=N' "$repo_root/scripts/inspect-openusd-foundations.sh"
  check_present 'skip_cleanup=True' "$repo_root/experiments/002-openusd-foundations/create_scene.py"

  local sim_line pxr_line
  sim_line="$(grep -n '^from isaacsim import SimulationApp$' "$repo_root/experiments/002-openusd-foundations/create_scene.py" | cut -d: -f1)"
  pxr_line="$(grep -n '^        from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux$' "$repo_root/experiments/002-openusd-foundations/create_scene.py" | cut -d: -f1)"
  [[ -n "$sim_line" && -n "$pxr_line" ]] || fail 'create_scene.py import order markers are missing'
  (( sim_line < pxr_line )) || fail 'SimulationApp is not imported before pxr modules'

  check_present 'openusd_foundations.usda' "$repo_root/experiments/002-openusd-foundations/create_scene.py"
  check_present 'openusd_foundations.usd' "$repo_root/experiments/002-openusd-foundations/create_scene.py"
  check_present 'PXR-USDC' "$repo_root/experiments/002-openusd-foundations/create_scene.py"
  check_present '#usda' "$repo_root/experiments/002-openusd-foundations/create_scene.py"
  check_present 'formatId' "$repo_root/experiments/002-openusd-foundations/create_scene.py"
  check_present 'formatId' "$repo_root/experiments/002-openusd-foundations/inspect_scene.py"
  check_present '/World/Lab/Marker' "$repo_root/experiments/002-openusd-foundations/create_scene.py"
  check_present '/World/Lab/Marker' "$repo_root/experiments/002-openusd-foundations/inspect_scene.py"
  check_present 'UsdGeom.Cylinder' "$repo_root/experiments/002-openusd-foundations/create_scene.py"
  check_present 'UsdGeom.Cube' "$repo_root/experiments/002-openusd-foundations/create_scene.py"
  check_present 'UsdGeom.Sphere' "$repo_root/experiments/002-openusd-foundations/create_scene.py"
  check_present 'UsdGeom.Xform' "$repo_root/experiments/002-openusd-foundations/create_scene.py"

  check_present '/workspace/experiments/002-openusd-foundations/output:rw' "$repo_root/scripts/run-openusd-foundations.sh"
  check_present '/workspace/experiments/002-openusd-foundations/results:rw' "$repo_root/scripts/run-openusd-foundations.sh"
  check_present '/workspace/experiments/002-openusd-foundations/output:rw' "$repo_root/scripts/inspect-openusd-foundations.sh"
  check_present '/workspace/experiments/002-openusd-foundations/results:rw' "$repo_root/scripts/inspect-openusd-foundations.sh"
  check_present 'openusd_foundations_output_dir' "$repo_root/scripts/run-openusd-foundations.sh"
  check_present 'openusd_foundations_results_dir' "$repo_root/scripts/run-openusd-foundations.sh"
  check_present 'openusd_foundations_output_dir' "$repo_root/scripts/inspect-openusd-foundations.sh"
  check_present 'openusd_foundations_results_dir' "$repo_root/scripts/inspect-openusd-foundations.sh"
  check_present 'openusd_foundations_runtime_root' "$repo_root/scripts/run-openusd-foundations.sh"
  check_present 'openusd_foundations_runtime_root' "$repo_root/scripts/inspect-openusd-foundations.sh"
  check_present 'prepare-openusd-lab-ownership' "$repo_root/Makefile"
  check_present 'validate-openusd-lab-ownership' "$repo_root/Makefile"
  check_present 'validate-openusd-lab' "$repo_root/Makefile"
  check_present 'run-openusd-lab' "$repo_root/Makefile"
  check_present 'inspect-openusd-lab' "$repo_root/Makefile"
  check_present 'docker run --rm --pull=never' "$repo_root/scripts/validate-openusd-foundations-ownership.sh"
  check_present 'ownership-write-check' "$repo_root/scripts/validate-openusd-foundations-ownership.sh"
  check_present 'stat -c "%u:%g"' "$repo_root/scripts/validate-openusd-foundations-ownership.sh"
  check_present 'rm -f "\$probe"' "$repo_root/scripts/validate-openusd-foundations-ownership.sh"

  local actual_paths expected_paths actual_runtime_paths expected_runtime_paths
  expected_paths="$(
    printf '%s\n' \
      "$(openusd_foundations_output_dir)" \
      "$(openusd_foundations_results_dir)" \
      "$(openusd_foundations_runtime_root)/cache/main" \
      "$(openusd_foundations_runtime_root)/cache/computecache" \
      "$(openusd_foundations_runtime_root)/cache/hub" \
      "$(openusd_foundations_runtime_root)/logs" \
      "$(openusd_foundations_runtime_root)/config" \
      "$(openusd_foundations_runtime_root)/data" \
      "$(openusd_foundations_runtime_root)/pkg"
  )"
  actual_paths="$(openusd_foundations_ownership_dirs)"
  [[ "$actual_paths" == "$expected_paths" ]] || fail 'OpenUSD foundations ownership path list changed unexpectedly'

  actual_runtime_paths="$(openusd_foundations_runtime_ownership_dirs)"
  expected_runtime_paths="$(
    printf '%s\n' \
      "$(openusd_foundations_runtime_root)/cache/main" \
      "$(openusd_foundations_runtime_root)/cache/computecache" \
      "$(openusd_foundations_runtime_root)/cache/hub" \
      "$(openusd_foundations_runtime_root)/logs" \
      "$(openusd_foundations_runtime_root)/config" \
      "$(openusd_foundations_runtime_root)/data" \
      "$(openusd_foundations_runtime_root)/pkg"
  )"
  [[ "$actual_runtime_paths" == "$expected_runtime_paths" ]] || fail 'OpenUSD foundations runtime path list changed unexpectedly'

  check_present 'output/*' "$repo_root/experiments/002-openusd-foundations/.gitignore"
  check_present 'results/*' "$repo_root/experiments/002-openusd-foundations/.gitignore"
  check_present '\*.usd' "$repo_root/experiments/002-openusd-foundations/.gitignore"
  check_present '\*.usda' "$repo_root/experiments/002-openusd-foundations/.gitignore"
  check_present '\*.log' "$repo_root/experiments/002-openusd-foundations/.gitignore"
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
      fail "Unknown mode: ${1:-}"
      ;;
  esac
}

main "$@"
