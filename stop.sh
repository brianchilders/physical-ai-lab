#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source "$script_dir/scripts/lib/env.sh"

verify_project_cleared() {
  local project_name="$1"
  local remaining_containers

  remaining_containers="$(
    docker ps -a \
      --filter "label=com.docker.compose.project=${project_name}" \
      --format '{{.Names}}'
  )"

  if [[ -n "$remaining_containers" ]]; then
    printf 'FAIL: Compose project %s still has containers:\n%s\n' \
      "$project_name" \
      "$remaining_containers" >&2
    return 1
  fi
}

main() {
  local repo_root_path compose_env

  load_lab_env
  require_docker
  require_docker_compose
  repo_root_path="$(repo_root)"
  compose_env="$(mktemp)"
  trap 'rm -f "${compose_env:-}"' EXIT

  write_compose_env_file "$compose_env"

  docker compose \
    --env-file "$compose_env" \
    --file "$repo_root_path/docker/isaac/compose.yaml" \
    --profile headless \
    -p isaac \
    down \
    --remove-orphans

  verify_project_cleared isaac
}

main "$@"
