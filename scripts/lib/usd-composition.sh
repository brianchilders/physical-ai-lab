#!/usr/bin/env bash

usd_composition_repo_root() {
  printf '%s\n' "$(repo_root)"
}

usd_composition_experiment_root() {
  printf '%s\n' "$(usd_composition_repo_root)/experiments/003-usd-composition"
}

usd_composition_runtime_root() {
  local root="${ISAAC_STORAGE_ROOT:-/mnt/nvme/isaac}"

  printf '%s\n' "${USD_COMPOSITION_RUNTIME_ROOT:-$root/experiments/003-usd-composition}"
}

usd_composition_assets_dir() {
  printf '%s\n' "$(usd_composition_runtime_root)/assets"
}

usd_composition_output_dir() {
  printf '%s\n' "$(usd_composition_runtime_root)/output"
}

usd_composition_results_dir() {
  printf '%s\n' "$(usd_composition_runtime_root)/results"
}

usd_composition_runtime_ownership_dirs() {
  local root
  root="$(usd_composition_runtime_root)"

  printf '%s\n' \
    "$root/assets" \
    "$root/output" \
    "$root/results" \
    "$root/cache/main" \
    "$root/cache/computecache" \
    "$root/cache/hub" \
    "$root/logs" \
    "$root/config" \
    "$root/data" \
    "$root/pkg"
}

usd_composition_source_assets() {
  printf '%s\n' \
    "$(usd_composition_experiment_root)/assets/red_cube.usda" \
    "$(usd_composition_experiment_root)/assets/blue_sphere.usda" \
    "$(usd_composition_experiment_root)/assets/yellow_marker.usda" \
    "$(usd_composition_experiment_root)/assets/ground.usda" \
    "$(usd_composition_experiment_root)/assets/payload_cluster.usda"
}

usd_composition_output_files() {
  printf '%s\n' \
    "$(usd_composition_output_dir)/lab_environment.usda" \
    "$(usd_composition_output_dir)/base_environment.usda" \
    "$(usd_composition_output_dir)/lighting_layer.usda" \
    "$(usd_composition_output_dir)/composition_root.usda" \
    "$(usd_composition_output_dir)/composition_wrapper.usda"
}

usd_composition_ownership_dirs() {
  usd_composition_runtime_ownership_dirs
}
