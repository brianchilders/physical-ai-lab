#!/usr/bin/env bash

isaac_runtime_owner() {
  printf '%s:%s\n' 1234 1234
}

isaac_runtime_ownership_dirs() {
  local root="${ISAAC_STORAGE_ROOT:-/mnt/nvme/isaac}"

  printf '%s\n' \
    "$root/cache/isaac-sim/main" \
    "$root/cache/isaac-sim/computecache" \
    "$root/cache/ov/hub" \
    "$root/logs/isaac-sim" \
    "$root/projects/isaac-sim/config" \
    "$root/projects/isaac-sim/data" \
    "$root/projects/isaac-sim/pkg"
}

isaac_runtime_data_dirs() {
  local root="${ISAAC_STORAGE_ROOT:-/mnt/nvme/isaac}"

  printf '%s\n' \
    "$root/assets" \
    "$root/datasets"
}

isaac_smoke_runtime_root() {
  local root="${ISAAC_STORAGE_ROOT:-/mnt/nvme/isaac}"

  printf '%s\n' "${ISAAC_SMOKE_RUNTIME_ROOT:-$root/smoke/001-first-launch}"
}

isaac_smoke_runtime_ownership_dirs() {
  local root
  root="$(isaac_smoke_runtime_root)"

  printf '%s\n' \
    "$root/cache/main" \
    "$root/cache/computecache" \
    "$root/cache/hub" \
    "$root/logs" \
    "$root/config" \
    "$root/data" \
    "$root/pkg"
}
