#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source "$script_dir/lib/env.sh"
# shellcheck disable=SC1091
source "$script_dir/lib/interactive-studio.sh"

main() {
  local name state

  load_lab_env
  require_docker

  name="$(interactive_studio_container_name)"

  state="$(interactive_studio_container_state)"

  case "$state" in
    running)
      printf 'PASS: stopping Interactive Studio before explicit restart: %s\n' "$name"
      "$script_dir/stop-interactive-studio.sh"
      ;;
    stopped)
      printf 'PASS: explicit restart will remove the stopped Interactive Studio container: %s\n' "$name"
      ;;
    absent)
      printf 'FAIL: Interactive Studio container does not exist for restart: %s\n' "$name" >&2
      exit 1
      ;;
  esac

  if [[ "$(interactive_studio_container_state)" != "stopped" ]]; then
    printf 'FAIL: Interactive Studio container is not stopped before restart: %s\n' "$name" >&2
    exit 1
  fi

  printf 'PASS: removing exact Interactive Studio container before recreation: %s\n' "$name"
  docker rm "$name" >/dev/null
  "$script_dir/start-interactive-studio.sh"
}

main "$@"
