readonly NVME_ROOT="/mnt/nvme"
declare -Ag VALIDATION_READINESS=()
declare -ag VALIDATION_READINESS_ORDER=(
  "Host"
  "GPU"
  "Storage"
  "Docker"
  "Vulkan"
  "Isaac image"
  "Container GPU"
  "Isaac runtime"
)

validation_section() {
  printf '\n== %s ==\n' "$*"
}

validation_pass() {
  printf 'PASS: %s\n' "$*"
}

validation_warn() {
  printf 'WARN: %s\n' "$*"
  VALIDATION_WARNINGS=$((VALIDATION_WARNINGS + 1))
}

validation_info() {
  printf 'INFO: %s\n' "$*"
}

validation_fail() {
  printf 'FAIL: %s\n' "$*" >&2
  VALIDATION_FAILURES=$((VALIDATION_FAILURES + 1))
}

validation_require_command() {
  if command -v "$1" >/dev/null 2>&1; then
    validation_pass "$1 is installed"
  else
    validation_fail "$1 is not installed"
  fi
}

validation_set_readiness() {
  local category="$1"
  local status="$2"
  local detail="${3:-}"

  if [[ -n "$detail" ]]; then
    VALIDATION_READINESS["$category"]="$status - $detail"
  else
    VALIDATION_READINESS["$category"]="$status"
  fi
}

validation_summary() {
  printf '\nSummary: %d failure(s), %d warning(s)\n' \
    "$VALIDATION_FAILURES" "$VALIDATION_WARNINGS"
  local category
  for category in "${VALIDATION_READINESS_ORDER[@]}"; do
    if [[ -n ${VALIDATION_READINESS[$category]+x} ]]; then
      printf '%s readiness: %s\n' "$category" "${VALIDATION_READINESS[$category]}"
    fi
  done
  if (( VALIDATION_FAILURES > 0 )); then
    return 1
  fi
}
