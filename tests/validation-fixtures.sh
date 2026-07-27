#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/.." && pwd)"

# shellcheck disable=SC1091
source "$repo_root/scripts/lib/env.sh"
# shellcheck disable=SC1091
source "$repo_root/scripts/validate/common.sh"
# shellcheck disable=SC1091
source "$repo_root/scripts/validate/vulkan.sh"
# shellcheck disable=SC1091
source "$repo_root/scripts/validate/docker.sh"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

reset_validation_state() {
  VALIDATION_FAILURES=0
  VALIDATION_WARNINGS=0
  VALIDATION_READINESS=()
}

make_stub_dir() {
  local dir
  dir="$(mktemp -d)"
  mkdir -p "$dir/bin"
  local tool real_tool
  for tool in cat grep sed awk sort cut head tr env; do
    real_tool="$(command -v "$tool")"
    cat >"$dir/bin/$tool" <<EOF
#!/bin/bash
exec "$real_tool" "\$@"
EOF
    chmod +x "$dir/bin/$tool"
  done
  printf '%s\n' "$dir"
}

make_no_rg_path() {
  local dir tool real_tool
  dir="$(mktemp -d)"
  mkdir -p "$dir/bin"

  for tool in bash git find grep sed awk sort cut head mktemp rm dirname pwd cat chmod env tr; do
    real_tool="$(command -v "$tool")"
    ln -s "$real_tool" "$dir/bin/$tool"
  done

  printf '%s\n' "$dir"
}

create_vulkan_stub() {
  local stub_dir="$1"
  local fixture_file="$2"
  local display_log_file="${3:-}"

  cat >"$stub_dir/bin/vulkaninfo" <<EOF
#!/bin/bash
if [[ -n "${display_log_file}" ]]; then
  printf '%s\n' "\${DISPLAY-}" >>"$display_log_file"
fi
cat "$fixture_file"
EOF
  chmod +x "$stub_dir/bin/vulkaninfo"
}

create_docker_stub() {
  local stub_dir="$1"

  cat >"$stub_dir/bin/docker" <<'EOF'
#!/bin/bash
set -euo pipefail

subcommand="${1:-}"
shift || true

case "$subcommand" in
  info)
    if [[ "${1:-}" == "--format" ]]; then
      case "${2:-}" in
        '{{json .Runtimes}}') printf '%s\n' "${DOCKER_INFO_RUNTIMES:-{\"nvidia\":{},\"runc\":{}}}" ;;
        '{{.DefaultRuntime}}') printf '%s\n' "${DOCKER_DEFAULT_RUNTIME:-runc}" ;;
        *) printf '%s\n' '{}' ;;
      esac
      exit 0
    fi
    printf '%s\n' "Docker info stub"
    exit 0
    ;;
  image)
    case "${1:-}" in
      ls)
        printf '%s\n' "${DOCKER_IMAGE_LS_OUTPUT:-}"
        exit 0
        ;;
      inspect)
        shift || true
        for image in "$@"; do
          if [[ "${DOCKER_IMAGE_INSPECT_SUCCESS:-}" == *"|${image}|"* ]]; then
            exit 0
          fi
        done
        exit 1
        ;;
    esac
    ;;
  run)
    local_image=""
    args=("$@")
    skip_next=0
    for arg in "${args[@]}"; do
      if (( skip_next )); then
        skip_next=0
        continue
      fi
      case "$arg" in
        --gpus)
          skip_next=1
          ;;
        --gpus=*)
          ;;
        -*)
          ;;
        *)
          local_image="$arg"
          break
          ;;
      esac
    done
    printf '%s\n' "$local_image" >>"${DOCKER_RUN_LOG_FILE:-/dev/null}"
    if [[ "${DOCKER_RUN_SUCCESS_IMAGES:-}" == *"|${local_image}|"* ]]; then
      exit 0
    fi
    exit 1
    ;;
  compose)
    exit 0
    ;;
esac

exit 1
EOF
  chmod +x "$stub_dir/bin/docker"
}

assert_readiness() {
  local category="$1"
  local expected="$2"
  local actual="${VALIDATION_READINESS[$category]:-}"

  [[ "$actual" == "$expected" ]] || fail "Expected $category readiness '$expected', got '${actual:-unset}'"
}

run_vulkan_case() {
  local name="$1"
  local fixture_file="$2"
  local display_mode="$3"
  local expected_readiness="$4"

  local stub_dir
  local old_path="$PATH"
  stub_dir="$(make_stub_dir)"
  create_vulkan_stub "$stub_dir" "$fixture_file"

  reset_validation_state
  PATH="$stub_dir/bin"
  if [[ "$display_mode" == "unset" ]]; then
    unset DISPLAY || true
  else
    export DISPLAY="$display_mode"
  fi

  validate_vulkan >/dev/null 2>&1
  assert_readiness "Vulkan" "$expected_readiness"

  PATH="$old_path"
  /bin/rm -rf "$stub_dir"
  printf 'PASS: %s\n' "$name"
}

run_vulkan_display_isolation_case() {
  local fixture_file="$1"
  local display_log_file
  local stub_dir
  local old_path="$PATH"
  display_log_file="$(mktemp)"
  stub_dir="$(make_stub_dir)"
  create_vulkan_stub "$stub_dir" "$fixture_file" "$display_log_file"

  reset_validation_state
  PATH="$stub_dir/bin"
  export DISPLAY=:0

  validate_vulkan >/dev/null 2>&1
  assert_readiness "Vulkan" "PASS"
  [[ "$(sed -n '1p' "$display_log_file")" == "" ]] || fail 'Vulkan validator inherited DISPLAY instead of stripping it'

  PATH="$old_path"
  /bin/rm -rf "$stub_dir"
  /bin/rm -f "$display_log_file"
  unset DISPLAY || true
  printf 'PASS: Vulkan validator strips inherited DISPLAY for headless enumeration\n'
}

run_vulkan_tests() {
  local fixture_dir="$repo_root/tests/fixtures/vulkan"

  run_vulkan_case \
    "Vulkan NVIDIA plus llvmpipe without DISPLAY" \
    "$fixture_dir/nvidia-titan-llvmpipe-no-display.txt" \
    "unset" \
    "PASS"

  run_vulkan_display_isolation_case \
    "$fixture_dir/nvidia-xcb-headless.txt"

  run_vulkan_case \
    "llvmpipe-only fixture correctly produced Vulkan failure" \
    "$fixture_dir/llvmpipe-only.txt" \
    "unset" \
    "FAIL - software renderer detected"

  run_vulkan_case \
    "Vulkan NVIDIA device with DISPLAY" \
    "$fixture_dir/nvidia-with-display.txt" \
    ":0" \
    "PASS"

  local stub_dir
  local old_path="$PATH"
  stub_dir="$(make_stub_dir)"
  reset_validation_state
  PATH="$stub_dir/bin"
  unset DISPLAY || true
  validate_vulkan >/dev/null 2>&1
  assert_readiness "Vulkan" "WARN - vulkaninfo missing"
  PATH="$old_path"
  /bin/rm -rf "$stub_dir"
  printf 'PASS: Vulkan missing binary case\n'
}

run_docker_case() {
  local name="$1"
  local image_ls_output="$2"
  local inspect_success="$3"
  local run_success="$4"
  local expected_readiness="$5"
  local expected_first_run="${6:-}"

  local stub_dir run_log
  local old_path="$PATH"
  stub_dir="$(make_stub_dir)"
  load_lab_env
  run_log="$stub_dir/run.log"
  create_docker_stub "$stub_dir"

  reset_validation_state
  export DOCKER_IMAGE_LS_OUTPUT="$image_ls_output"
  export DOCKER_IMAGE_INSPECT_SUCCESS="$inspect_success"
  export DOCKER_RUN_SUCCESS_IMAGES="$run_success"
  export DOCKER_RUN_LOG_FILE="$run_log"
  PATH="$stub_dir/bin"

  validate_runtime >/dev/null 2>&1
  assert_readiness "Container GPU" "$expected_readiness"

  if [[ -n "$expected_first_run" ]]; then
    local first_run
    first_run="$(sed -n '1p' "$run_log")"
    [[ "$first_run" == "$expected_first_run" ]] || fail "Expected first runtime image '$expected_first_run', got '$first_run'"
  fi

  PATH="$old_path"
  /bin/rm -rf "$stub_dir"
  unset DOCKER_IMAGE_LS_OUTPUT DOCKER_IMAGE_INSPECT_SUCCESS DOCKER_RUN_SUCCESS_IMAGES DOCKER_RUN_LOG_FILE
  printf 'PASS: %s\n' "$name"
}

run_no_rg_case() {
  local stub_dir old_path phase2_script
  stub_dir="$(make_no_rg_path)"
  old_path="$PATH"
  phase2_script="$repo_root/tests/phase2-refinement.sh"

  PATH="$stub_dir/bin"
  "$phase2_script" bash-syntax >/dev/null 2>&1
  "$phase2_script" policy-check >/dev/null 2>&1
  "$phase2_script" config-check >/dev/null 2>&1

  PATH="$old_path"
  /bin/rm -rf "$stub_dir"
  printf 'PASS: Phase 2 suite runs without rg\n'
}

run_docker_tests() {
  run_docker_case \
    "Docker discovery picks nvidia/cuda base image" \
    $'nvidia/cuda:12.9.1-base-ubuntu24.04\nnvidia/cuda:12.9.1-runtime-ubuntu24.04' \
    '|' \
    '|nvidia/cuda:12.9.1-base-ubuntu24.04|' \
    "PASS - GPU passthrough succeeded" \
    "nvidia/cuda:12.9.1-base-ubuntu24.04"

  run_docker_case \
    "Docker discovery picks nvcr.io/nvidia/cuda image" \
    $'nvcr.io/nvidia/cuda:12.9.1-runtime-ubuntu24.04\nhello-world:latest' \
    '|' \
    '|nvcr.io/nvidia/cuda:12.9.1-runtime-ubuntu24.04|' \
    "PASS - GPU passthrough succeeded" \
    "nvcr.io/nvidia/cuda:12.9.1-runtime-ubuntu24.04"

  run_docker_case \
    "Docker discovery prefers the best of multiple local candidates" \
    $'nvidia/cuda:12.9.1-devel-ubuntu24.04\nnvidia/cuda:12.9.1-base-ubuntu24.04\nnvcr.io/nvidia/cuda:12.9.1-runtime-ubuntu24.04' \
    '|' \
    '|nvidia/cuda:12.9.1-base-ubuntu24.04|' \
    "PASS - GPU passthrough succeeded" \
    "nvidia/cuda:12.9.1-base-ubuntu24.04"

  run_docker_case \
    "Docker discovery skips unrelated local images" \
    $'hello-world:latest\nbusybox:latest' \
    '|' \
    '|' \
    "NOT TESTED"

  run_docker_case \
    "simulated GPU-passthrough failure was correctly detected" \
    $'nvidia/cuda:12.9.1-base-ubuntu24.04' \
    '|' \
    '|' \
    "FAIL - GPU passthrough failed"

  run_docker_case \
    "Docker discovery prefers pinned Isaac image when present" \
    $'nvidia/cuda:12.9.1-base-ubuntu24.04\nnvcr.io/nvidia/cuda:12.9.1-runtime-ubuntu24.04' \
    '|nvcr.io/nvidia/isaac-sim:6.0.1|' \
    '|nvcr.io/nvidia/isaac-sim:6.0.1|' \
    "PASS - GPU passthrough succeeded" \
    "nvcr.io/nvidia/isaac-sim:6.0.1"
}

main() {
  case "${1:-all}" in
    vulkan) run_vulkan_tests ;;
    docker) run_docker_tests ;;
    no-rg) run_no_rg_case ;;
    all)
      run_vulkan_tests
      run_docker_tests
      run_no_rg_case
      ;;
    *)
      fail "Unknown mode: ${1:-}"
      ;;
  esac
}

main "$@"
