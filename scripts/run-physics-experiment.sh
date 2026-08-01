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

  set -o pipefail
  docker run --rm --pull=never \
    --name physics-foundations-004-run \
    --gpus all \
    --user 1234:1234 \
    --entrypoint bash \
    -e ACCEPT_EULA=Y \
    -e PRIVACY_CONSENT=N \
    -e PHYSICS_FOUNDATIONS_RUNTIME_ROOT="$runtime_root" \
    -v "$repo_root_path:/workspace:ro" \
    -v /mnt/nvme/isaac:/mnt/nvme/isaac:rw \
    -v "$runtime_root/cache/main:/isaac-sim/.cache:rw" \
    -v "$runtime_root/cache/computecache:/isaac-sim/.nv/ComputeCache:rw" \
    -v "$runtime_root/cache/hub:/var/cache/hub:rw" \
    -v "$runtime_root/logs:/isaac-sim/.nvidia-omniverse/logs:rw" \
    -v "$runtime_root/config:/isaac-sim/.nvidia-omniverse/config:rw" \
    -v "$runtime_root/data:/isaac-sim/.local/share/ov/data:rw" \
    -v "$runtime_root/pkg:/isaac-sim/.local/share/ov/pkg:rw" \
    -w /workspace/experiments/004-physics-foundations \
    nvcr.io/nvidia/isaac-sim:6.0.1 \
    -lc 'set -o pipefail; /isaac-sim/python.sh run_physics_experiment.py 2>&1 | tee /mnt/nvme/isaac/experiments/004-physics-foundations/results/run_physics_experiment.log; exit "${PIPESTATUS[0]}"'

  exit "${PIPESTATUS[0]}"
}

main "$@"
