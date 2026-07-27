#!/usr/bin/env bash

repo_root() {
  git rev-parse --show-toplevel
}

require_command() {
  local command_name="$1"
  local message="${2:-$1 is required}"

  if ! command -v "$command_name" >/dev/null 2>&1; then
    printf 'FAIL: %s\n' "$message" >&2
    exit 1
  fi
}

require_docker() {
  require_command docker "Docker is not installed"
}

require_docker_compose() {
  if ! docker compose version >/dev/null 2>&1; then
    printf 'FAIL: Docker Compose is not available\n' >&2
    exit 1
  fi
}

if [[ "${LAB_ENV_VARS_INITIALIZED:-0}" != 1 ]]; then
  readonly -a LAB_ENV_VARS=(
    LAB_HOSTNAME
    ISAAC_STORAGE_ROOT
    ISAAC_SIM_REGISTRY
    ISAAC_SIM_REPOSITORY
    ISAAC_SIM_TAG
    DGX_SPARK_ENABLED
    JETSON_ENABLED
    ROS2_ENABLED
    ISAAC_SIM_NAME
    ISAAC_SIM_UID
    ISAAC_SIM_GID
    ACCEPT_EULA
    PRIVACY_CONSENT
    PRIVACY_USERID
    ISAACSIM_HOST
    ISAACSIM_SIGNAL_PORT
    ISAACSIM_STREAM_PORT
    DISPLAY
    XAUTHORITY
    COMPOSE_PROJECT_NAME
  )
  readonly LAB_ENV_VARS_INITIALIZED=1
fi

load_lab_env() {
  local root file var
  local -A saved_values=()
  local -a saved_names=()

  root="$(repo_root)"

  for var in "${LAB_ENV_VARS[@]}"; do
    if [[ -v "$var" ]]; then
      saved_names+=("$var")
      saved_values["$var"]="${!var}"
    fi
  done

  for file in \
    "$root/config/lab.env.example" \
    "$root/.env.example" \
    "$root/.env"
  do
    [[ -f "$file" ]] || continue
    # shellcheck disable=SC1090
    source "$file"
  done

  for var in "${saved_names[@]}"; do
    export "$var=${saved_values[$var]}"
  done

  for var in "${LAB_ENV_VARS[@]}"; do
    if [[ -v $var ]]; then
      export "$var"
    fi
  done
}

compose_file_path() {
  printf '%s\n' "$(repo_root)/docker/isaac/compose.yaml"
}

isaac_image_ref() {
  printf '%s/%s:%s\n' \
    "${ISAAC_SIM_REGISTRY:?unset ISAAC_SIM_REGISTRY}" \
    "${ISAAC_SIM_REPOSITORY:?unset ISAAC_SIM_REPOSITORY}" \
    "${ISAAC_SIM_TAG:?unset ISAAC_SIM_TAG}"
}

write_compose_env_file() {
  local out="$1"
  local var
  local include_gui="${2:-no}"

  : >"$out"
  for var in "${LAB_ENV_VARS[@]}"; do
    if [[ "$include_gui" != "yes" && ( "$var" == "DISPLAY" || "$var" == "XAUTHORITY" ) ]]; then
      continue
    fi
    if [[ -v $var ]]; then
      printf '%s=%s\n' "$var" "${!var}" >>"$out"
    fi
  done
}

write_gui_compose_env_file() {
  write_compose_env_file "$1" yes
}
