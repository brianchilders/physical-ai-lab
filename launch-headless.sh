#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source "$script_dir/scripts/lib/env.sh"

die() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

main() {
  local repo_root_path compose_env

  load_lab_env
  require_docker
  require_docker_compose
  repo_root_path="$(repo_root)"
  compose_env="$(mktemp)"
  trap 'rm -f "${compose_env:-}"' EXIT

  ./scripts/validate-runtime-ownership.sh

  write_compose_env_file "$compose_env"

  exec docker compose \
    --env-file "$compose_env" \
    --file "$repo_root_path/docker/isaac/compose.yaml" \
    --profile headless \
    up \
    -d \
    --no-build \
    headless
}

main "$@"
