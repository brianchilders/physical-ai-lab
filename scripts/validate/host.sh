validate_host() {
  validation_section "Host"

  if [[ -r /etc/os-release ]]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    if [[ "${ID:-}" == "ubuntu" && "${VERSION_ID:-}" == 24.04* ]]; then
      validation_pass "Ubuntu ${VERSION_ID:-unknown} detected"
    else
      validation_fail "Ubuntu 24.04 is required, found ${PRETTY_NAME:-unknown}"
    fi
  else
    validation_fail "/etc/os-release is unavailable"
  fi

  validation_pass "Kernel: $(uname -r)"

  case "$(uname -m)" in
    x86_64) validation_pass "Architecture: x86_64" ;;
    *) validation_fail "Architecture must be x86_64, found $(uname -m)" ;;
  esac

  if [[ -n "${SSH_CONNECTION:-}" || -n "${SSH_TTY:-}" ]]; then
    validation_pass "Session appears to be SSH"
  else
    validation_pass "Session appears to be local"
  fi
}

