#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source "$script_dir/lib/env.sh"
# shellcheck disable=SC1091
source "$script_dir/lib/interactive-studio.sh"

main() {
  local name

  load_lab_env
  require_docker
  name="$(interactive_studio_container_name)"

  docker exec -it --user 1234:1234 "$name" bash
}

main "$@"
