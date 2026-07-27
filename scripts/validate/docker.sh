validate_docker() {
  validation_section "Docker"

  validation_require_command docker

  if ! command -v docker >/dev/null 2>&1; then
    return
  fi

  if ! docker info >/dev/null 2>&1; then
    validation_fail "Docker daemon is not reachable"
    return
  fi

  validation_pass "Docker daemon is reachable"

  local runtimes default_runtime
  runtimes=$(docker info --format '{{json .Runtimes}}' 2>/dev/null || true)
  default_runtime=$(docker info --format '{{.DefaultRuntime}}' 2>/dev/null || true)

  if [[ "$runtimes" == *'"nvidia"'* ]]; then
    validation_pass "Docker NVIDIA runtime is configured"
  else
    validation_fail "Docker NVIDIA runtime is not configured"
  fi

  if [[ -n "$default_runtime" ]]; then
    validation_pass "Default Docker runtime: $default_runtime"
  fi

  local isaac_image gpu_test_image
  isaac_image="$(isaac_image_ref)"

  if docker image inspect "$isaac_image" >/dev/null 2>&1; then
    validation_pass "Isaac Sim image present locally: $isaac_image"
    gpu_test_image="$isaac_image"
  elif docker image inspect nvcr.io/nvidia/cuda:12.8.0-base-ubuntu24.04 >/dev/null 2>&1; then
    validation_pass "Local CUDA test image available for passthrough smoke test"
    gpu_test_image="nvcr.io/nvidia/cuda:12.8.0-base-ubuntu24.04"
  else
    validation_warn "No local container image available for a passthrough smoke test"
    return
  fi

  if docker run --rm --pull=never --gpus all --runtime=nvidia "$gpu_test_image" nvidia-smi >/dev/null 2>&1; then
    validation_pass "Docker GPU passthrough works with $gpu_test_image"
  else
    validation_fail "Docker GPU passthrough test failed with $gpu_test_image"
  fi
}
