#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source "$script_dir/scripts/lib/env.sh"
# shellcheck disable=SC1091
source "$script_dir/scripts/validate/common.sh"
# shellcheck disable=SC1091
source "$script_dir/scripts/validate/host.sh"
# shellcheck disable=SC1091
source "$script_dir/scripts/validate/gpu.sh"
# shellcheck disable=SC1091
source "$script_dir/scripts/validate/docker.sh"
# shellcheck disable=SC1091
source "$script_dir/scripts/validate/storage.sh"
# shellcheck disable=SC1091
source "$script_dir/scripts/validate/vulkan.sh"
# shellcheck disable=SC1091
source "$script_dir/scripts/validate/isaac.sh"

main() {
  local host_name user_name

  load_lab_env

  VALIDATION_FAILURES=0
  VALIDATION_WARNINGS=0

  validation_section "Session"
  host_name="$(hostname)"
  user_name="$(id -un)"
  validation_pass "Host: $host_name"
  validation_pass "User: $user_name"
  validation_pass "Working directory: $(pwd)"

  validate_host
  validate_gpu
  validate_storage
  validate_docker
  validate_vulkan
  validate_isaac

  validation_summary
}

main "$@"
