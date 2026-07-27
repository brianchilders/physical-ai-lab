#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source "$script_dir/lib/env.sh"
# shellcheck disable=SC1091
source "$script_dir/lib/usd-composition.sh"

main() {
  local repo_root_path runtime_root
  local mode="${1:-composition}"

  load_lab_env
  require_docker
  repo_root_path="$(repo_root)"
  runtime_root="$(usd_composition_runtime_root)"

  mkdir -p \
    "$(usd_composition_assets_dir)" \
    "$(usd_composition_output_dir)" \
    "$(usd_composition_results_dir)" \
    "$runtime_root/cache/main" \
    "$runtime_root/cache/computecache" \
    "$runtime_root/cache/hub" \
    "$runtime_root/logs" \
    "$runtime_root/config" \
    "$runtime_root/data" \
    "$runtime_root/pkg"

  set -o pipefail
  docker run --rm --pull=never \
    --name usd-composition-003 \
    --gpus all \
    --user 1234:1234 \
    --entrypoint bash \
    -e ACCEPT_EULA=Y \
    -e PRIVACY_CONSENT=N \
    -v "$repo_root_path:/workspace:ro" \
    -v "$(usd_composition_assets_dir):/mnt/nvme/isaac/experiments/003-usd-composition/assets:rw" \
    -v "$(usd_composition_output_dir):/mnt/nvme/isaac/experiments/003-usd-composition/output:rw" \
    -v "$(usd_composition_results_dir):/mnt/nvme/isaac/experiments/003-usd-composition/results:rw" \
    -v "$runtime_root/cache/main:/isaac-sim/.cache:rw" \
    -v "$runtime_root/cache/computecache:/isaac-sim/.nv/ComputeCache:rw" \
    -v "$runtime_root/cache/hub:/var/cache/hub:rw" \
    -v "$runtime_root/logs:/isaac-sim/.nvidia-omniverse/logs:rw" \
    -v "$runtime_root/config:/isaac-sim/.nvidia-omniverse/config:rw" \
    -v "$runtime_root/data:/isaac-sim/.local/share/ov/data:rw" \
    -v "$runtime_root/pkg:/isaac-sim/.local/share/ov/pkg:rw" \
    -w /workspace/experiments/003-usd-composition \
    nvcr.io/nvidia/isaac-sim:6.0.1 \
    -lc "set -o pipefail; if [[ '$mode' == 'assets' ]]; then /isaac-sim/python.sh create_assets.py 2>&1 | tee /mnt/nvme/isaac/experiments/003-usd-composition/results/create_assets.log; else /isaac-sim/python.sh create_composition.py 2>&1 | tee /mnt/nvme/isaac/experiments/003-usd-composition/results/create_composition.log; fi; exit \"\${PIPESTATUS[0]}\""

  exit "${PIPESTATUS[0]}"
}

main "$@"
