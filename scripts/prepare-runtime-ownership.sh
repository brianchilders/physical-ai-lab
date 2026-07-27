#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source "$script_dir/lib/env.sh"
# shellcheck disable=SC1091
source "$script_dir/lib/isaac-runtime.sh"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

main() {
  local target_owner path

  load_lab_env

  if [[ "${CONFIRM_CHOWN:-}" != "1" ]]; then
    fail "Set CONFIRM_CHOWN=1 to prepare Isaac Sim runtime ownership."
  fi

  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    fail "Run this target with sudo so chown can apply the supported Isaac Sim ownership."
  fi

  target_owner="$(isaac_runtime_owner)"

  printf 'Target owner: %s\n' "$target_owner"
  printf 'Approved paths:\n'
  while IFS= read -r path; do
    [[ -n "$path" ]] || continue
    printf '  %s -> %s\n' "$path" "$target_owner"
  done < <(isaac_runtime_ownership_dirs)

  while IFS= read -r path; do
    [[ -n "$path" ]] || continue
    [[ -e "$path" ]] || fail "Missing required runtime path: $path. Run ./prepare-storage.sh first."
  done < <(isaac_runtime_ownership_dirs)

  while IFS= read -r path; do
    [[ -n "$path" ]] || continue
    chown 1234:1234 "$path"
  done < <(isaac_runtime_ownership_dirs)
}

main "$@"
