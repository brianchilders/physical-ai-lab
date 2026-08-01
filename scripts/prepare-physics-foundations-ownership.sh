#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source "$script_dir/lib/env.sh"
# shellcheck disable=SC1091
source "$script_dir/lib/physics-foundations.sh"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

main() {
  local target_owner root
  local -a approved_paths

  load_lab_env
  root="$(physics_foundations_runtime_root)"

  approved_paths=(
    "$root/output"
    "$root/results"
    "$root/output/run-01"
    "$root/output/run-02"
    "$root/results/run-01"
    "$root/results/run-02"
    "$root/cache/main"
    "$root/cache/computecache"
    "$root/cache/hub"
    "$root/logs"
    "$root/config"
    "$root/data"
    "$root/pkg"
  )

  if [[ "${CONFIRM_CHOWN:-}" != "1" ]]; then
    fail 'Set CONFIRM_CHOWN=1 to prepare Phase 6 ownership.'
  fi

  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    fail 'Run this target with sudo so chown can apply the supported 1234:1234 identity.'
  fi

  target_owner='1234:1234'

  printf 'Target owner: %s\n' "$target_owner"
  printf 'Approved paths:\n'
  for path in "${approved_paths[@]}"; do
    printf '  %s -> %s\n' "$path" "$target_owner"
    mkdir -p "$path"
    chown 1234:1234 "$path"
  done
}

main "$@"
