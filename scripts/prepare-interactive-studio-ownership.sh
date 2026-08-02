#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source "$script_dir/lib/env.sh"
# shellcheck disable=SC1091
source "$script_dir/lib/interactive-studio.sh"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

main() {
  local expected_workspace_owner path

  load_lab_env

  if [[ "${CONFIRM_CHOWN:-}" != "1" ]]; then
    fail "Set CONFIRM_CHOWN=1 to prepare Interactive Studio ownership."
  fi

  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    fail "Run this target with elevated privileges outside Codex."
  fi

  expected_workspace_owner="${INTERACTIVE_STUDIO_WORKSPACE_OWNER:-1000:1000}"

  printf 'Interactive Studio ownership targets:\n'
  printf '  runtime owner: 1234:1234\n'
  printf '  workspace owner: %s\n' "$expected_workspace_owner"
  printf '  shared assets: read-only, untouched\n'

  while IFS= read -r path; do
    [[ -n "$path" ]] || continue
    printf '  runtime %s -> 1234:1234\n' "$path"
    [[ -e "$path" ]] || fail "Missing runtime path: $path"
    chown 1234:1234 "$path"
  done < <(interactive_studio_runtime_paths)

  while IFS= read -r path; do
    [[ -n "$path" ]] || continue
    printf '  workspace %s -> group 1000 with setgid\n' "$path"
    [[ -e "$path" ]] || fail "Missing workspace path: $path"
    chgrp "${INTERACTIVE_STUDIO_SHARED_GID:-1000}" "$path"
    chmod 2775 "$path"
  done < <(interactive_studio_workspace_paths)
}

main "$@"
