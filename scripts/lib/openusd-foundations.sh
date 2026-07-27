#!/usr/bin/env bash

openusd_foundations_root() {
  printf '%s\n' "${OPENUSD_FOUNDATIONS_ROOT:-$(repo_root)/experiments/002-openusd-foundations}"
}

openusd_foundations_output_dir() {
  printf '%s\n' "$(openusd_foundations_runtime_root)/output"
}

openusd_foundations_results_dir() {
  printf '%s\n' "$(openusd_foundations_runtime_root)/results"
}

openusd_foundations_runtime_root() {
  local root="${ISAAC_STORAGE_ROOT:-/mnt/nvme/isaac}"

  printf '%s\n' "${OPENUSD_FOUNDATIONS_RUNTIME_ROOT:-$root/experiments/002-openusd-foundations}"
}

openusd_foundations_runtime_ownership_dirs() {
  local root
  root="$(openusd_foundations_runtime_root)"

  printf '%s\n' \
    "$root/cache/main" \
    "$root/cache/computecache" \
    "$root/cache/hub" \
    "$root/logs" \
    "$root/config" \
    "$root/data" \
    "$root/pkg"
}

openusd_foundations_ownership_dirs() {
  printf '%s\n' \
    "$(openusd_foundations_output_dir)" \
    "$(openusd_foundations_results_dir)"
  openusd_foundations_runtime_ownership_dirs
}
