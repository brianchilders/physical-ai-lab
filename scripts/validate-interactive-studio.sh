#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source "$script_dir/lib/env.sh"
# shellcheck disable=SC1091
source "$script_dir/lib/interactive-studio.sh"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

report() {
  printf 'PASS: %s\n' "$*"
}

main() {
  local host_ip

  load_lab_env

  case "$(uname -m)" in
    x86_64|aarch64)
      report "Supported host architecture: $(uname -m)"
      ;;
    *)
      fail "Unsupported host architecture: $(uname -m)"
      ;;
  esac

  require_docker
  docker info >/dev/null
  report "Docker daemon is reachable"

  if ! docker info 2>/dev/null | grep -Eq 'Runtimes:.*nvidia|nvidia'; then
    fail "NVIDIA container runtime is not visible in docker info"
  fi

  if ! docker image inspect "$(interactive_studio_image_ref)" >/dev/null 2>&1; then
    fail "Pinned Interactive Studio image is not present locally: $(interactive_studio_image_ref)"
  fi

  for var in $(interactive_studio_required_env_vars); do
    if [[ "$var" == INTERACTIVE_STUDIO_HOST_IP ]]; then
      host_ip="${!var:-}"
      if ! interactive_studio_validate_host_ip "$host_ip"; then
        fail "Invalid required environment variable ${var}: ${host_ip:-<unset>}"
      fi
      continue
    fi
    [[ -n "${!var:-}" || "$var" == INTERACTIVE_STUDIO_HOST_IP ]] || fail "Missing required environment variable: $var"
  done

  interactive_studio_validate_no_phase6_reuse || fail "Interactive Studio reuses a Phase 6 path"
  interactive_studio_validate_mount_boundary || fail "Interactive Studio mount boundary is invalid"
  interactive_studio_validate_port_availability || fail "Interactive Studio ports are not available"

  case "$(interactive_studio_container_state)" in
    absent)
      report "Interactive Studio container is absent"
      ;;
    stopped)
      report "Interactive Studio container exists but is stopped"
      ;;
    running)
      report "Interactive Studio container is already running"
      ;;
  esac

  printf 'PASS: launch prerequisites validated without starting Isaac Sim\n'
}

main "$@"
