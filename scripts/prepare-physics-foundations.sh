#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source "$script_dir/lib/env.sh"
# shellcheck disable=SC1091
source "$script_dir/lib/physics-foundations.sh"

main() {
  local path

  load_lab_env

  printf 'Preparing Phase 6 physics foundations directories\n'
  while IFS= read -r path; do
    [[ -n "$path" ]] || continue
    mkdir -p "$path"
    printf '  %s\n' "$path"
  done < <(physics_foundations_runtime_ownership_dirs)

  while IFS= read -r path; do
    [[ -n "$path" ]] || continue
    mkdir -p "$path"
    printf '  %s\n' "$path"
  done < <(printf '%s\n' \
    "$(physics_foundations_output_dir)/run-01" \
    "$(physics_foundations_output_dir)/run-02" \
    "$(physics_foundations_results_dir)/run-01" \
    "$(physics_foundations_results_dir)/run-02")
}

main "$@"
