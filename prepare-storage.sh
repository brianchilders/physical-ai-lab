#!/usr/bin/env bash
set -euo pipefail

readonly STORAGE_ROOT="${ISAAC_STORAGE_ROOT:-/mnt/nvme/isaac}"
readonly NVME_ROOT="/mnt/nvme"

# shellcheck disable=SC1091
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/scripts/lib/isaac-runtime.sh"

log() {
  printf '%s\n' "$*"
}

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

require_mount() {
  [[ -d "$NVME_ROOT" ]] || fail "$NVME_ROOT does not exist"
  if ! findmnt -rn "$NVME_ROOT" >/dev/null 2>&1; then
    fail "$NVME_ROOT is not mounted"
  fi
}

main() {
  require_mount

  log "Using storage root: $STORAGE_ROOT"
  log "Available space on $NVME_ROOT:"
  df -h "$NVME_ROOT"

  local -a dirs=(
    "$STORAGE_ROOT"
    "$STORAGE_ROOT/cache"
    "$STORAGE_ROOT/cache/ov"
    "$STORAGE_ROOT/logs"
    "$STORAGE_ROOT/projects"
    "$STORAGE_ROOT/projects/isaac-sim"
  )

  for dir in "${dirs[@]}"; do
    mkdir -p "$dir"
    log "Ensured: $dir"
  done

  while IFS= read -r dir; do
    [[ -n "$dir" ]] || continue
    mkdir -p "$dir"
    log "Ensured Isaac runtime dir: $dir"
  done < <(isaac_runtime_ownership_dirs)

  while IFS= read -r dir; do
    [[ -n "$dir" ]] || continue
    mkdir -p "$dir"
    log "Ensured Isaac data dir: $dir"
  done < <(isaac_runtime_data_dirs)

  log "Storage preparation complete."
}

main "$@"
