#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/.." && pwd)"

# shellcheck disable=SC1091
source "$repo_root/scripts/lib/env.sh"
# shellcheck disable=SC1091
source "$repo_root/scripts/lib/physics-foundations.sh"

main() {
  load_lab_env
  require_docker

  local repo_root_path

  repo_root_path="$(repo_root)"

  set -o pipefail
  docker run --rm --pull=never \
    --name physics-foundations-004-compare \
    --user 1234:1234 \
    --entrypoint bash \
    -e PHYSICS_FOUNDATIONS_RUNTIME_ROOT=/mnt/nvme/isaac/experiments/004-physics-foundations \
    -v "$repo_root_path:/workspace:ro" \
    -v /mnt/nvme/isaac:/mnt/nvme/isaac:rw \
    -w /workspace/experiments/004-physics-foundations \
    nvcr.io/nvidia/isaac-sim:6.0.1 \
    -lc '/isaac-sim/python.sh compare_physics_runs.py'
}

main "$@"
