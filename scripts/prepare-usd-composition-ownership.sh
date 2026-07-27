#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source "$script_dir/lib/env.sh"
# shellcheck disable=SC1091
source "$script_dir/lib/usd-composition.sh"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

main() {
  local target_owner path

  load_lab_env

  if [[ "${CONFIRM_CHOWN:-}" != "1" ]]; then
    fail 'Set CONFIRM_CHOWN=1 to prepare USD composition ownership.'
  fi

  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    fail 'Run this target with sudo so chown can apply the supported 1234:1234 identity.'
  fi

  target_owner='1234:1234'

  printf 'Target owner: %s\n' "$target_owner"
  printf 'Approved paths:\n'
  while IFS= read -r path; do
    [[ -n "$path" ]] || continue
    printf '  %s -> %s\n' "$path" "$target_owner"
  done < <(usd_composition_runtime_ownership_dirs)

  while IFS= read -r path; do
    [[ -n "$path" ]] || continue
    mkdir -p "$path"
    chown 1234:1234 "$path"
  done < <(usd_composition_runtime_ownership_dirs)
}

main "$@"
