readonly NVME_ROOT="/mnt/nvme"

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

validation_summary() {
  printf '\nSummary: %d failure(s), %d warning(s)\n' \
    "$VALIDATION_FAILURES" "$VALIDATION_WARNINGS"
  if (( VALIDATION_FAILURES > 0 )); then
    return 1
  fi
}
