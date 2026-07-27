#!/usr/bin/env bash
set -euo pipefail

readonly STORAGE_ROOT="${ISAAC_STORAGE_ROOT:-/mnt/nvme/isaac}"
readonly NVME_ROOT="/mnt/nvme"

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
    "$STORAGE_ROOT/cache/isaac-sim"
    "$STORAGE_ROOT/cache/isaac-sim/main"
    "$STORAGE_ROOT/cache/isaac-sim/computecache"
    "$STORAGE_ROOT/cache/ov"
    "$STORAGE_ROOT/cache/ov/hub"
    "$STORAGE_ROOT/assets"
    "$STORAGE_ROOT/datasets"
    "$STORAGE_ROOT/logs"
    "$STORAGE_ROOT/logs/isaac-sim"
    "$STORAGE_ROOT/projects"
    "$STORAGE_ROOT/projects/isaac-sim"
    "$STORAGE_ROOT/projects/isaac-sim/config"
    "$STORAGE_ROOT/projects/isaac-sim/data"
    "$STORAGE_ROOT/projects/isaac-sim/pkg"
  )

  for dir in "${dirs[@]}"; do
    mkdir -p "$dir"
    log "Ensured: $dir"
  done

  log "Storage preparation complete."
}

main "$@"

