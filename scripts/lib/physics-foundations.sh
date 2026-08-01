#!/usr/bin/env bash

physics_foundations_repo_root() {
  printf '%s\n' "$(repo_root)"
}

physics_foundations_experiment_root() {
  printf '%s\n' "$(physics_foundations_repo_root)/experiments/004-physics-foundations"
}

physics_foundations_runtime_root() {
  local root="${ISAAC_STORAGE_ROOT:-/mnt/nvme/isaac}"

  printf '%s\n' "${PHYSICS_FOUNDATIONS_RUNTIME_ROOT:-$root/experiments/004-physics-foundations}"
}

physics_foundations_output_dir() {
  printf '%s\n' "$(physics_foundations_runtime_root)/output"
}

physics_foundations_results_dir() {
  printf '%s\n' "$(physics_foundations_runtime_root)/results"
}

physics_foundations_run_output_dir() {
  printf '%s\n' "$(physics_foundations_output_dir)/${1:?run-id required}"
}

physics_foundations_run_results_dir() {
  printf '%s\n' "$(physics_foundations_results_dir)/${1:?run-id required}"
}

physics_foundations_runtime_ownership_dirs() {
  local root
  root="$(physics_foundations_runtime_root)"

  printf '%s\n' \
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

physics_foundations_ownership_dirs() {
  physics_foundations_runtime_ownership_dirs
}

physics_foundations_output_files() {
  printf '%s\n' \
    "$(physics_foundations_output_dir)/physics_scene.usda" \
    "$(physics_foundations_output_dir)/physics_scene.usd" \
    "$(physics_foundations_output_dir)/run-01/physics_scene.usda" \
    "$(physics_foundations_output_dir)/run-01/physics_scene.usd" \
    "$(physics_foundations_output_dir)/run-02/physics_scene.usda" \
    "$(physics_foundations_output_dir)/run-02/physics_scene.usd"
}

physics_foundations_result_files() {
  printf '%s\n' \
    "$(physics_foundations_results_dir)/run-01/step_metrics.csv" \
    "$(physics_foundations_results_dir)/run-01/summary.json" \
    "$(physics_foundations_results_dir)/run-02/step_metrics.csv" \
    "$(physics_foundations_results_dir)/run-02/summary.json" \
    "$(physics_foundations_results_dir)/comparison.csv" \
    "$(physics_foundations_results_dir)/comparison.json" \
    "$(physics_foundations_results_dir)/summary.md"
}
