#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/.." && pwd)"

# shellcheck disable=SC1091
source "$repo_root/scripts/lib/env.sh"
# shellcheck disable=SC1091
source "$repo_root/scripts/lib/usd-composition.sh"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
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
    "$repo_root/experiments/003-usd-composition/create_assets.py" \
    "$repo_root/experiments/003-usd-composition/create_composition.py" \
    "$repo_root/experiments/003-usd-composition/inspect_composition.py"
}

run_policy_checks() {
  local files=(
    "$repo_root/experiments/003-usd-composition"
    "$repo_root/scripts/lib/usd-composition.sh"
    "$repo_root/scripts/prepare-usd-composition.sh"
    "$repo_root/scripts/prepare-usd-composition-ownership.sh"
    "$repo_root/scripts/validate-usd-composition-ownership.sh"
    "$repo_root/scripts/run-usd-composition.sh"
    "$repo_root/scripts/inspect-usd-composition.sh"
    "$repo_root/Makefile"
  )

  check_not_present 'https?://|omniverse://|ngc://' "${files[@]}"
  check_not_present 'ros2|rclpy|ROS 2|ros-core' "${files[@]}"
  check_not_present 'Isaac Lab|isaaclab' "${files[@]}"
  check_not_present 'DGX Spark|dgx spark' "${files[@]}"
  check_not_present 'docker pull|--pull=always' \
    "$repo_root/scripts/run-usd-composition.sh" \
    "$repo_root/scripts/inspect-usd-composition.sh" \
    "$repo_root/scripts/validate-usd-composition-ownership.sh"
  check_not_present '--network=host' \
    "$repo_root/scripts/run-usd-composition.sh" \
    "$repo_root/scripts/inspect-usd-composition.sh" \
    "$repo_root/scripts/validate-usd-composition-ownership.sh" \
    "$repo_root/Makefile"
  check_not_present 'docker .*prune|system prune|image prune|volume prune' \
    "$repo_root/scripts" \
    "$repo_root/Makefile"

  check_present '--pull=never' "$repo_root/scripts/run-usd-composition.sh"
  check_present '--pull=never' "$repo_root/scripts/inspect-usd-composition.sh"
  check_present '--pull=never' "$repo_root/scripts/validate-usd-composition-ownership.sh"
  check_present '--user 1234:1234' "$repo_root/scripts/run-usd-composition.sh"
  check_present '--user 1234:1234' "$repo_root/scripts/inspect-usd-composition.sh"
  check_present '--user 1234:1234' "$repo_root/scripts/validate-usd-composition-ownership.sh"
  check_present ':/workspace:ro' "$repo_root/scripts/run-usd-composition.sh"
  check_present ':/workspace:ro' "$repo_root/scripts/inspect-usd-composition.sh"
  check_present 'usd_composition_assets_dir' "$repo_root/scripts/run-usd-composition.sh"
  check_present 'usd_composition_output_dir' "$repo_root/scripts/run-usd-composition.sh"
  check_present 'usd_composition_results_dir' "$repo_root/scripts/run-usd-composition.sh"
  check_present 'usd_composition_assets_dir' "$repo_root/scripts/inspect-usd-composition.sh"
  check_present 'usd_composition_output_dir' "$repo_root/scripts/inspect-usd-composition.sh"
  check_present 'usd_composition_results_dir' "$repo_root/scripts/inspect-usd-composition.sh"
  check_present 'ACCEPT_EULA=Y' "$repo_root/scripts/run-usd-composition.sh"
  check_present 'PRIVACY_CONSENT=N' "$repo_root/scripts/run-usd-composition.sh"
  check_present 'ACCEPT_EULA=Y' "$repo_root/scripts/inspect-usd-composition.sh"
  check_present 'PRIVACY_CONSENT=N' "$repo_root/scripts/inspect-usd-composition.sh"

  check_present 'CONFIRM_CHOWN' "$repo_root/scripts/prepare-usd-composition-ownership.sh"
  check_present '1234:1234' "$repo_root/scripts/prepare-usd-composition-ownership.sh"
  check_present 'chown 1234:1234' "$repo_root/scripts/prepare-usd-composition-ownership.sh"
  check_present 'stat -c "%u:%g"' "$repo_root/scripts/validate-usd-composition-ownership.sh"
  check_present 'rm -f "\$probe"' "$repo_root/scripts/validate-usd-composition-ownership.sh"
  check_present 'skip_cleanup=True' "$repo_root/experiments/003-usd-composition/create_assets.py"
  check_present 'skip_cleanup=True' "$repo_root/experiments/003-usd-composition/create_composition.py"
  check_not_present 'skip_cleanup=' "$repo_root/experiments/003-usd-composition/inspect_composition.py"

  check_present 'composition_wrapper.usda' "$repo_root/experiments/003-usd-composition/create_composition.py"
  check_present 'composition_root.usda' "$repo_root/experiments/003-usd-composition/create_composition.py"
  check_present 'lighting_layer.usda' "$repo_root/experiments/003-usd-composition/create_composition.py"
  check_present 'base_environment.usda' "$repo_root/experiments/003-usd-composition/create_composition.py"
  check_present 'lab_environment.usda' "$repo_root/experiments/003-usd-composition/create_composition.py"
  check_present 'LoadNone' "$repo_root/experiments/003-usd-composition/create_composition.py"
  check_present 'GetPayloads\(\)\.AddPayload' "$repo_root/experiments/003-usd-composition/create_composition.py"
  check_present 'subLayerPaths = \["lighting_layer.usda", "base_environment.usda"\]' "$repo_root/experiments/003-usd-composition/create_composition.py"
  check_present 'xformOp:translate' "$repo_root/experiments/003-usd-composition/create_composition.py"
  check_present 'GetPropertyStack' "$repo_root/experiments/003-usd-composition/inspect_composition.py"
  check_present 'GetPrimStack' "$repo_root/experiments/003-usd-composition/inspect_composition.py"
  check_present 'source-asset-hashes.txt' "$repo_root/experiments/003-usd-composition/create_assets.py"
  check_present 'os._exit\(0\)' "$repo_root/experiments/003-usd-composition/inspect_composition.py"
  check_present 'os._exit\(1\)' "$repo_root/experiments/003-usd-composition/inspect_composition.py"
  check_present 'flush_streams' "$repo_root/experiments/003-usd-composition/inspect_composition.py"
  check_present 'sys.stdout.flush' "$repo_root/experiments/003-usd-composition/inspect_composition.py"
  check_present 'sys.stderr.flush' "$repo_root/experiments/003-usd-composition/inspect_composition.py"
  check_present 'COMPOSITION_INSPECT: terminating one-shot inspector' "$repo_root/experiments/003-usd-composition/inspect_composition.py"
  check_present 'app = SimulationApp\(\{"headless": True\}\)' "$repo_root/experiments/003-usd-composition/inspect_composition.py"
  check_not_present 'SimulationApp\.close' "$repo_root/experiments/003-usd-composition/inspect_composition.py"
  check_present 'traceback.print_exc' "$repo_root/experiments/003-usd-composition/inspect_composition.py"
  check_present 'raise RuntimeError' "$repo_root/experiments/003-usd-composition/inspect_composition.py"
  check_present 'run-usd-composition-assets' "$repo_root/Makefile"
  check_present 'run-usd-composition' "$repo_root/Makefile"
  check_present 'inspect-usd-composition' "$repo_root/Makefile"
  check_present 'test-phase5' "$repo_root/Makefile"

  local expected_paths actual_paths
  expected_paths="$(
    printf '%s\n' \
      "$(usd_composition_runtime_root)/assets" \
      "$(usd_composition_output_dir)" \
      "$(usd_composition_results_dir)" \
      "$(usd_composition_runtime_root)/cache/main" \
      "$(usd_composition_runtime_root)/cache/computecache" \
      "$(usd_composition_runtime_root)/cache/hub" \
      "$(usd_composition_runtime_root)/logs" \
      "$(usd_composition_runtime_root)/config" \
      "$(usd_composition_runtime_root)/data" \
      "$(usd_composition_runtime_root)/pkg"
  )"
  actual_paths="$(usd_composition_ownership_dirs)"
  [[ "$actual_paths" == "$expected_paths" ]] || fail 'USD composition ownership path list changed unexpectedly'

  check_present 'output/\*' "$repo_root/experiments/003-usd-composition/.gitignore"
  check_present 'results/\*' "$repo_root/experiments/003-usd-composition/.gitignore"
  check_present '\*.usd' "$repo_root/experiments/003-usd-composition/.gitignore"
  check_present '\*.usda' "$repo_root/experiments/003-usd-composition/.gitignore"
  check_present '\*.log' "$repo_root/experiments/003-usd-composition/.gitignore"
  check_present ':/mnt/nvme/isaac/experiments/003-usd-composition/assets:ro' "$repo_root/scripts/inspect-usd-composition.sh"
  check_present ':/mnt/nvme/isaac/experiments/003-usd-composition/output:ro' "$repo_root/scripts/inspect-usd-composition.sh"
  check_present ':/mnt/nvme/isaac/experiments/003-usd-composition/results:rw' "$repo_root/scripts/inspect-usd-composition.sh"
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
