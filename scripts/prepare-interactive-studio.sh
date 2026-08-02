#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source "$script_dir/lib/env.sh"
# shellcheck disable=SC1091
source "$script_dir/lib/interactive-studio.sh"

main() {
  local path

  load_lab_env

  printf 'Preparing Interactive Studio directories\n'
  while IFS= read -r path; do
    [[ -n "$path" ]] || continue
    mkdir -p "$path"
    printf '  %s\n' "$path"
  done < <(interactive_studio_runtime_paths)

  while IFS= read -r path; do
    [[ -n "$path" ]] || continue
    mkdir -p "$path"
    printf '  %s\n' "$path"
  done < <(interactive_studio_workspace_paths)
}

main "$@"
