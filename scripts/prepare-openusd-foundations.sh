#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source "$script_dir/lib/env.sh"
# shellcheck disable=SC1091
source "$script_dir/lib/openusd-foundations.sh"

main() {
  local path

  load_lab_env

  printf 'Preparing OpenUSD foundations directories\n'

  while IFS= read -r path; do
    [[ -n "$path" ]] || continue
    mkdir -p "$path"
    printf '  %s\n' "$path"
  done < <(openusd_foundations_local_ownership_dirs)

  while IFS= read -r path; do
    [[ -n "$path" ]] || continue
    mkdir -p "$path"
    printf '  %s\n' "$path"
  done < <(openusd_foundations_runtime_ownership_dirs)
}

main "$@"
