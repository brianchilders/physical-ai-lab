validate_gpu() {
  validation_section "GPU"
  local start_failures="$VALIDATION_FAILURES"
  local status="PASS"

  if ! command -v nvidia-smi >/dev/null 2>&1; then
    validation_fail "nvidia-smi is unavailable"
    validation_set_readiness "GPU" "FAIL"
    return
  fi

  local gpu_lines
  if ! gpu_lines=$(nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader 2>/dev/null); then
    validation_fail "nvidia-smi failed"
    validation_set_readiness "GPU" "FAIL"
    return
  fi

  validation_pass "GPU detected"
  while IFS= read -r line; do
    [[ -n "$line" ]] || continue
    validation_pass "$line"
  done <<<"$gpu_lines"

  if (( VALIDATION_FAILURES > start_failures )); then
    status="FAIL"
  fi

  validation_set_readiness "GPU" "$status"
}
