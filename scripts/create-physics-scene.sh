#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source "$script_dir/lib/env.sh"
# shellcheck disable=SC1091
source "$script_dir/lib/physics-foundations.sh"

main() {
  local repo_root_path runtime_root

  load_lab_env
  require_docker
  repo_root_path="$(repo_root)"
  runtime_root="$(physics_foundations_runtime_root)"

  mkdir -p \
    "$(physics_foundations_output_dir)" \
    "$runtime_root/cache/main" \
    "$runtime_root/cache/computecache" \
    "$runtime_root/cache/hub" \
    "$runtime_root/logs" \
    "$runtime_root/config" \
    "$runtime_root/data" \
    "$runtime_root/pkg"

  set -o pipefail
  docker run --rm --pull=never \
    --name physics-foundations-004-create \
    --gpus all \
    --user 1234:1234 \
    --entrypoint bash \
    -e ACCEPT_EULA=Y \
    -e PRIVACY_CONSENT=N \
    -e PHYSICS_FOUNDATIONS_RUNTIME_ROOT="$runtime_root" \
    -v "$repo_root_path:/workspace:ro" \
    -v /mnt/nvme/isaac:/mnt/nvme/isaac:rw \
    -w /workspace/experiments/004-physics-foundations \
    nvcr.io/nvidia/isaac-sim:6.0.1 \
    -lc 'set -o pipefail; /isaac-sim/python.sh create_physics_scene.py'

  exit "${PIPESTATUS[0]}"
}

main "$@"
