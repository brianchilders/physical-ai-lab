validate_docker() {
  validation_section "Docker"
  local start_failures="$VALIDATION_FAILURES"
  local status="PASS"

  validation_require_command docker

  if ! command -v docker >/dev/null 2>&1; then
    validation_set_readiness "Docker" "FAIL"
    return
  fi

  if ! docker info >/dev/null 2>&1; then
    validation_fail "Docker daemon is not reachable"
    validation_set_readiness "Docker" "FAIL"
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

  if (( VALIDATION_FAILURES > start_failures )); then
    status="FAIL"
  fi

  validation_set_readiness "Docker" "$status"
}

docker_runtime_candidate_score() {
  local image_ref="$1"

  case "$image_ref" in
    *base*ubuntu24.04*) printf '%s\n' 0 ;;
    *runtime*ubuntu24.04*) printf '%s\n' 1 ;;
    *base*ubuntu*) printf '%s\n' 2 ;;
    *runtime*ubuntu*) printf '%s\n' 3 ;;
    *base*) printf '%s\n' 4 ;;
    *runtime*) printf '%s\n' 5 ;;
    *devel*ubuntu24.04*) printf '%s\n' 6 ;;
    *devel*ubuntu*) printf '%s\n' 7 ;;
    *devel*) printf '%s\n' 8 ;;
    *) printf '%s\n' 9 ;;
  esac
}

docker_discover_local_cuda_images() {
  docker image ls --format '{{.Repository}}:{{.Tag}}' \
    | awk '
        /^nvidia\/cuda:/ || /^nvcr\.io\/nvidia\/cuda:/ { print }
      ' \
    | sort -u
}

docker_runtime_candidates() {
  local -a candidates=()
  local image_ref

  while IFS= read -r image_ref; do
    [[ -n "$image_ref" ]] || continue
    candidates+=("$image_ref")
  done < <(docker_discover_local_cuda_images)

  local scored
  for image_ref in "${candidates[@]}"; do
    printf '%s\t%s\n' "$(docker_runtime_candidate_score "$image_ref")" "$image_ref"
  done | sort -n -k1,1 -k2,2 | cut -f2-
}

validate_runtime() {
  validation_section "Container GPU"
  local status="NOT TESTED"
  local pinned_image runtime_image last_error=""
  local -a candidates=()

  if ! command -v docker >/dev/null 2>&1; then
    validation_warn "Docker is unavailable; GPU passthrough smoke test not tested"
    validation_set_readiness "Container GPU" "NOT TESTED"
    return
  fi

  if ! docker info >/dev/null 2>&1; then
    validation_warn "Docker daemon is unavailable; GPU passthrough smoke test not tested"
    validation_set_readiness "Container GPU" "NOT TESTED"
    return
  fi

  pinned_image="$(isaac_image_ref)"

  if docker image inspect "$pinned_image" >/dev/null 2>&1; then
    candidates=("$pinned_image")
    validation_pass "Pinned Isaac Sim image is present locally: $pinned_image"
  else
    while IFS= read -r runtime_image; do
      [[ -n "$runtime_image" ]] || continue
      candidates+=("$runtime_image")
    done < <(docker_runtime_candidates)
  fi

  if ((${#candidates[@]} == 0)); then
    validation_warn "No suitable local image available for a GPU passthrough smoke test"
    validation_set_readiness "Container GPU" "NOT TESTED"
    return
  fi

  for runtime_image in "${candidates[@]}"; do
    if docker run --rm --pull=never --gpus all "$runtime_image" nvidia-smi >/dev/null 2>&1; then
      validation_pass "Docker GPU passthrough works with $runtime_image"
      validation_set_readiness "Container GPU" "PASS" "GPU passthrough succeeded"
      return
    fi
    last_error="$runtime_image"
  done

  validation_fail "Docker GPU passthrough test failed with $last_error"
  validation_set_readiness "Container GPU" "FAIL" "GPU passthrough failed"
}
