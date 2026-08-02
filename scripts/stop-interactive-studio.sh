#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source "$script_dir/lib/env.sh"
# shellcheck disable=SC1091
source "$script_dir/lib/interactive-studio.sh"

report() {
  printf 'PASS: %s\n' "$*"
}

main() {
  local name state

  load_lab_env
  require_docker

  name="$(interactive_studio_container_name)"
  state="$(interactive_studio_container_state)"

  case "$state" in
    absent)
      report "Interactive Studio container absent: $name"
      exit 0
      ;;
    stopped)
      report "Interactive Studio container already stopped and retained: $name"
      exit 0
      ;;
  esac

  docker stop "$name" >/dev/null

  if [[ "$(interactive_studio_container_state)" == "running" ]]; then
    printf 'FAIL: Interactive Studio container is still running after stop: %s\n' "$name" >&2
    exit 1
  fi

  report "Interactive Studio container stopped and retained: $name"
}

main "$@"
