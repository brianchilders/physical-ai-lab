#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source "$script_dir/scripts/lib/env.sh"

die() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

require_dir() {
  [[ -d "$1" ]] || die "Missing required directory: $1. Run ./prepare-storage.sh first."
}

main() {
  local repo_root_path compose_env image_ref

  load_lab_env
  require_docker
  require_docker_compose

  if [[ -z "${DISPLAY:-}" ]]; then
    die "DISPLAY is not set. GUI mode requires a local desktop session."
  fi

  if [[ -z "${XAUTHORITY:-}" || ! -e "${XAUTHORITY}" ]]; then
    die "XAUTHORITY is not available. GUI mode needs local X11 authorization."
  fi

  repo_root_path="$(repo_root)"
  compose_env="$(mktemp)"
  trap 'rm -f "${compose_env:-}"' EXIT

  require_dir "$ISAAC_STORAGE_ROOT/cache/isaac-sim/main"
  require_dir "$ISAAC_STORAGE_ROOT/cache/isaac-sim/computecache"
  require_dir "$ISAAC_STORAGE_ROOT/cache/ov/hub"
  require_dir "$ISAAC_STORAGE_ROOT/logs/isaac-sim"
  require_dir "$ISAAC_STORAGE_ROOT/projects/isaac-sim/config"
  require_dir "$ISAAC_STORAGE_ROOT/projects/isaac-sim/data"
  require_dir "$ISAAC_STORAGE_ROOT/projects/isaac-sim/pkg"

  image_ref="$(isaac_image_ref)"
  if ! docker image inspect "$image_ref" >/dev/null 2>&1; then
    die "Docker image not found locally: $image_ref. Download it later with the official NVIDIA workflow."
  fi

  write_gui_compose_env_file "$compose_env"

  exec docker compose \
    --env-file "$compose_env" \
    --file "$repo_root_path/docker/isaac/compose.yaml" \
    --profile gui \
    up \
    -d \
    --no-build \
    gui
}

main "$@"
