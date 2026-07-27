#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/.." && pwd)"

# shellcheck disable=SC1091
source "$repo_root/scripts/lib/env.sh"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

run_shellcheck() {
  if ! command -v shellcheck >/dev/null 2>&1; then
    printf 'SKIP: shellcheck is not installed\n'
    return 0
  fi

  mapfile -t sh_files < <(cd "$repo_root" && rg --files -g '*.sh')
  if ((${#sh_files[@]} == 0)); then
    printf 'SKIP: no shell scripts found\n'
    return 0
  fi

  shellcheck "${sh_files[@]/#/$repo_root/}"
}

run_bash_syntax() {
  mapfile -t sh_files < <(cd "$repo_root" && rg --files -g '*.sh')
  if ((${#sh_files[@]} == 0)); then
    fail 'No shell scripts found'
  fi

  bash -n "${sh_files[@]/#/$repo_root/}"
}

run_config_check() {
  load_lab_env

  [[ "${ISAAC_SIM_REGISTRY}" == "nvcr.io" ]] || fail "Unexpected registry: ${ISAAC_SIM_REGISTRY}"
  [[ "${ISAAC_SIM_REPOSITORY}" == "nvidia/isaac-sim" ]] || fail "Unexpected repository: ${ISAAC_SIM_REPOSITORY}"
  [[ "${ISAAC_SIM_TAG}" == "6.0.1" ]] || fail "Unexpected tag: ${ISAAC_SIM_TAG}"

  local image_ref
  image_ref="$(isaac_image_ref)"
  [[ "$image_ref" == "nvcr.io/nvidia/isaac-sim:6.0.1" ]] || fail "Unexpected image ref: $image_ref"

  (
    export ISAAC_SIM_TAG=9.9.9
    load_lab_env
    [[ "$ISAAC_SIM_TAG" == "9.9.9" ]] || fail "Shell environment did not win precedence"
  )

  rg -n '^ISAAC_STORAGE_ROOT=' "$repo_root/.env.example" >/dev/null 2>&1 && \
    fail '.env.example should not define ISAAC_STORAGE_ROOT'
  rg -n '^ISAAC_SIM_(REGISTRY|REPOSITORY|TAG)=' "$repo_root/.env.example" >/dev/null 2>&1 && \
    fail '.env.example should not define pinned Isaac Sim image variables'

  [[ -f "$repo_root/config/lab.env.example" ]] || fail "Missing config/lab.env.example"
  [[ -f "$repo_root/.env.example" ]] || fail "Missing .env.example"

  if rg -n '/mnt/nvme/(cache|assets|datasets|logs|projects)' \
    "$repo_root/docker/isaac/compose.yaml" \
    "$repo_root/docs" \
    "$repo_root/assets/README.md" \
    "$repo_root/datasets/README.md" \
    "$repo_root/launch-headless.sh" \
    "$repo_root/launch-gui.sh" \
    "$repo_root/prepare-storage.sh" \
    "$repo_root/scripts" \
    "$repo_root/stop.sh" >/dev/null 2>&1; then
    fail 'Found forbidden alternate storage paths under /mnt/nvme/* outside isaac/'
  fi
}

run_compose_check() {
  load_lab_env
  require_docker
  require_docker_compose
  local compose_env
  compose_env="$(mktemp)"
  trap 'rm -f "${compose_env:-}"' EXIT
  write_compose_env_file "$compose_env"

  docker compose \
    --env-file "$compose_env" \
    --file "$repo_root/docker/isaac/compose.yaml" \
    config >/dev/null
}

run_image_status() {
  load_lab_env
  require_docker
  local image_ref
  image_ref="$(isaac_image_ref)"
  if docker image inspect "$image_ref" >/dev/null 2>&1; then
    printf 'PASS: Image present locally: %s\n' "$image_ref"
  else
    printf 'WARN: Image not present locally: %s\n' "$image_ref"
  fi
}

run_policy_check() {
  if rg -n 'docker pull|docker login' \
    "$repo_root/launch-headless.sh" \
    "$repo_root/launch-gui.sh" \
    "$repo_root/stop.sh" \
    "$repo_root/Makefile" \
    "$repo_root/docker/isaac/compose.yaml" >/dev/null 2>&1; then
    fail 'Found forbidden automatic pull/login commands'
  fi

  if rg -n 'privileged:' "$repo_root/docker/isaac/compose.yaml" >/dev/null 2>&1; then
    fail 'Found privileged container setting'
  fi

  if rg -n '/var/run/docker.sock' "$repo_root/docker/isaac/compose.yaml" >/dev/null 2>&1; then
    fail 'Found Docker socket mount'
  fi

  if rg -n 'docker run' "$repo_root/launch-headless.sh" "$repo_root/launch-gui.sh" "$repo_root/stop.sh" >/dev/null 2>&1; then
    fail 'Launch wrappers still contain docker run'
  fi

  if rg -n 'mkdir -p|rm -rf|chown|chmod|tee|apt-get|systemctl' "$repo_root/scripts/validate" >/dev/null 2>&1; then
    fail 'Validation scripts contain mutating commands'
  fi
}

main() {
  local mode="${1:-all}"

  case "$mode" in
    all)
      run_bash_syntax
      run_policy_check
      run_config_check
      run_compose_check
      run_image_status
      run_shellcheck
      ;;
    bash-syntax) run_bash_syntax ;;
    policy-check) run_policy_check ;;
    config-check) run_config_check ;;
    compose-check) run_compose_check ;;
    image-status) run_image_status ;;
    shellcheck) run_shellcheck ;;
    *)
      fail "Unknown mode: $mode"
      ;;
  esac
}

main "$@"
