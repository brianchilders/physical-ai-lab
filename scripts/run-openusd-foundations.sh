#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source "$script_dir/lib/env.sh"
# shellcheck disable=SC1091
source "$script_dir/lib/openusd-foundations.sh"

main() {
  local repo_root_path output_log runtime_root

  load_lab_env
  require_docker
  repo_root_path="$(repo_root)"
  runtime_root="$(openusd_foundations_runtime_root)"

  mkdir -p \
    "$(openusd_foundations_output_dir)" \
    "$(openusd_foundations_results_dir)" \
    "$runtime_root/cache/main" \
    "$runtime_root/cache/computecache" \
    "$runtime_root/cache/hub" \
    "$runtime_root/logs" \
    "$runtime_root/config" \
    "$runtime_root/data" \
    "$runtime_root/pkg"

  set -o pipefail
  docker run --rm --pull=never \
    --name openusd-foundations-002 \
    --gpus all \
    --user 1234:1234 \
    --entrypoint bash \
    -e ACCEPT_EULA=Y \
    -e PRIVACY_CONSENT=N \
    -v "$repo_root_path:/workspace:ro" \
    -v "$(openusd_foundations_output_dir):/workspace/experiments/002-openusd-foundations/output:rw" \
    -v "$(openusd_foundations_results_dir):/workspace/experiments/002-openusd-foundations/results:rw" \
    -v "$runtime_root/cache/main:/isaac-sim/.cache:rw" \
    -v "$runtime_root/cache/computecache:/isaac-sim/.nv/ComputeCache:rw" \
    -v "$runtime_root/cache/hub:/var/cache/hub:rw" \
    -v "$runtime_root/logs:/isaac-sim/.nvidia-omniverse/logs:rw" \
    -v "$runtime_root/config:/isaac-sim/.nvidia-omniverse/config:rw" \
    -v "$runtime_root/data:/isaac-sim/.local/share/ov/data:rw" \
    -v "$runtime_root/pkg:/isaac-sim/.local/share/ov/pkg:rw" \
    -w /workspace/experiments/002-openusd-foundations \
    nvcr.io/nvidia/isaac-sim:6.0.1 \
    -lc 'set -o pipefail; /isaac-sim/python.sh create_scene.py 2>&1 | tee /workspace/experiments/002-openusd-foundations/results/create_scene.log; exit "${PIPESTATUS[0]}"'

  exit "${PIPESTATUS[0]}"
}

main "$@"
