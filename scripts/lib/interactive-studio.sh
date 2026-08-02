#!/usr/bin/env bash

interactive_studio_fail() {
  printf 'FAIL: %s\n' "$*" >&2
  return 1
}

interactive_studio_repo_root() {
  printf '%s\n' "$(repo_root)"
}

interactive_studio_root() {
  printf '%s\n' "${INTERACTIVE_STUDIO_ROOT:-/mnt/nvme/isaac/interactive-studio}"
}

interactive_studio_workspace_root() {
  printf '%s\n' "${INTERACTIVE_STUDIO_WORKSPACE_ROOT:-$(interactive_studio_root)/workspace}"
}

interactive_studio_assets_root() {
  printf '%s\n' "${INTERACTIVE_STUDIO_ASSETS_ROOT:-/mnt/nvme/isaac/assets}"
}

interactive_studio_container_name() {
  printf '%s\n' "${INTERACTIVE_STUDIO_CONTAINER_NAME:-interactive-studio}"
}

interactive_studio_image_ref() {
  printf '%s\n' "${INTERACTIVE_STUDIO_IMAGE_REF:-nvcr.io/nvidia/isaac-sim:6.0.1}"
}

interactive_studio_shared_gid() {
  printf '%s\n' "${INTERACTIVE_STUDIO_SHARED_GID:-1000}"
}

interactive_studio_signal_port() {
  printf '%s\n' "${INTERACTIVE_STUDIO_SIGNAL_PORT:-49100}"
}

interactive_studio_stream_port() {
  printf '%s\n' "${INTERACTIVE_STUDIO_STREAM_PORT:-47998}"
}

interactive_studio_host_ip() {
  printf '%s\n' "${INTERACTIVE_STUDIO_HOST_IP:-}"
}

interactive_studio_workspace_umask() {
  printf '%s\n' '0002'
}

interactive_studio_runtime_paths() {
  local root
  root="$(interactive_studio_root)"

  printf '%s\n' \
    "$root" \
    "$root/cache/main" \
    "$root/cache/computecache" \
    "$root/cache/hub" \
    "$root/config" \
    "$root/data" \
    "$root/logs" \
    "$root/pkg" \
    "$root/sessions"
}

interactive_studio_workspace_paths() {
  local root
  root="$(interactive_studio_workspace_root)"

  printf '%s\n' \
    "$root" \
    "$root/projects" \
    "$root/working-scenes" \
    "$root/exports" \
    "$root/captures" \
    "$root/screenshots" \
    "$root/scratch"
}

interactive_studio_shared_asset_paths() {
  printf '%s\n' "$(interactive_studio_assets_root)"
}

interactive_studio_mount_specs() {
  local repo_root_path assets_root runtime_root workspace_root

  repo_root_path="$(interactive_studio_repo_root)"
  assets_root="$(interactive_studio_assets_root)"
  runtime_root="$(interactive_studio_root)"
  workspace_root="$(interactive_studio_workspace_root)"

  printf '%s\n' \
    "$repo_root_path|/workspace/repo|ro|repository" \
    "$assets_root|$assets_root|ro|shared_assets" \
    "$runtime_root/cache/main|/isaac-sim/.cache|rw|runtime_cache_main" \
    "$runtime_root/cache/computecache|/isaac-sim/.nv/ComputeCache|rw|runtime_cache_compute" \
    "$runtime_root/cache/hub|/var/cache/hub|rw|runtime_cache_hub" \
    "$runtime_root/config|/isaac-sim/.nvidia-omniverse/config|rw|runtime_config" \
    "$runtime_root/data|/isaac-sim/.local/share/ov/data|rw|runtime_data" \
    "$runtime_root/logs|/isaac-sim/.nvidia-omniverse/logs|rw|runtime_logs" \
    "$runtime_root/pkg|/isaac-sim/.local/share/ov/pkg|rw|runtime_pkg" \
    "$runtime_root/sessions|$runtime_root/sessions|rw|runtime_sessions" \
    "$workspace_root|$workspace_root|rw|interactive_workspace"
}

interactive_studio_required_env_vars() {
  printf '%s\n' \
    INTERACTIVE_STUDIO_ROOT \
    INTERACTIVE_STUDIO_WORKSPACE_ROOT \
    INTERACTIVE_STUDIO_ASSETS_ROOT \
    INTERACTIVE_STUDIO_CONTAINER_NAME \
    INTERACTIVE_STUDIO_IMAGE_REF \
    INTERACTIVE_STUDIO_SHARED_GID \
    INTERACTIVE_STUDIO_HOST_IP \
    INTERACTIVE_STUDIO_SIGNAL_PORT \
    INTERACTIVE_STUDIO_STREAM_PORT
}

interactive_studio_readiness_markers() {
  printf '%s\n' \
    'Isaac Sim Full Streaming App is loaded.' \
    'Isaac Sim Headless WebRTC App is loaded.' \
    'Isaac Sim App is loaded.'
}

interactive_studio_container_state() {
  local name
  name="$(interactive_studio_container_name)"

  if ! docker inspect "$name" >/dev/null 2>&1; then
    printf '%s\n' absent
    return 0
  fi

  docker inspect -f '{{if .State.Running}}running{{else}}stopped{{end}}' "$name"
}

interactive_studio_container_exists() {
  [[ "$(interactive_studio_container_state)" != "absent" ]]
}

interactive_studio_container_running() {
  [[ "$(interactive_studio_container_state)" == "running" ]]
}

interactive_studio_validate_host_ip() {
  local host_ip="${1:-}"
  local bridge_gateway=""

  [[ -n "$host_ip" ]] || return 1
  [[ "$host_ip" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]] || return 1

  IFS=. read -r a b c d <<<"$host_ip"
  for octet in "$a" "$b" "$c" "$d"; do
    [[ "$octet" =~ ^[0-9]+$ ]] || return 1
    (( octet >= 0 && octet <= 255 )) || return 1
  done

  case "$host_ip" in
    0.0.0.0|127.0.0.1|255.255.255.255)
      return 1
      ;;
    172.17.*.*|172.18.*.*|192.168.65.1)
      return 1
      ;;
  esac

  if command -v docker >/dev/null 2>&1; then
    bridge_gateway="$(docker network inspect bridge -f '{{(index .IPAM.Config 0).Gateway}}' 2>/dev/null || true)"
    if [[ -n "$bridge_gateway" && "$host_ip" == "$bridge_gateway" ]]; then
      return 1
    fi
  fi

  return 0
}

interactive_studio_validate_no_phase6_reuse() {
  local root workspace_root

  root="$(interactive_studio_root)"
  workspace_root="$(interactive_studio_workspace_root)"

  case "$root" in
    /mnt/nvme/isaac/experiments/004-physics-foundations*|/workspace/experiments/004-physics-foundations*)
      return 1
      ;;
  esac

  case "$workspace_root" in
    /mnt/nvme/isaac/experiments/004-physics-foundations*|/workspace/experiments/004-physics-foundations*)
      return 1
      ;;
  esac

  return 0
}

interactive_studio_validate_required_paths() {
  local path

  while IFS= read -r path; do
    [[ -n "$path" ]] || continue
    [[ -e "$path" ]] || return 1
  done < <(interactive_studio_runtime_paths)

  while IFS= read -r path; do
    [[ -n "$path" ]] || continue
    [[ -e "$path" ]] || return 1
  done < <(interactive_studio_workspace_paths)

  [[ -d "$(interactive_studio_assets_root)" ]] || return 1
  return 0
}

interactive_studio_validate_port_availability() {
  local tcp_port udp_port
  tcp_port="$(interactive_studio_signal_port)"
  udp_port="$(interactive_studio_stream_port)"

  if command -v ss >/dev/null 2>&1; then
    if ss -H -ltn "sport = :$tcp_port" | grep -q .; then
      return 1
    fi
    if ss -H -lun "sport = :$udp_port" | grep -q .; then
      return 1
    fi
  fi

  return 0
}

interactive_studio_validate_mount_boundary() {
  local root workspace_root assets_root

  root="$(interactive_studio_root)"
  workspace_root="$(interactive_studio_workspace_root)"
  assets_root="$(interactive_studio_assets_root)"

  [[ "$assets_root" != "$root" ]] || return 1
  [[ "$workspace_root" != "$root" ]] || return 1
  [[ "$workspace_root" != "$assets_root" ]] || return 1
  [[ "$(interactive_studio_repo_root)" != "$root" ]] || return 1
  [[ "$(interactive_studio_repo_root)" != "$workspace_root" ]] || return 1
  [[ "$(interactive_studio_repo_root)" != "$assets_root" ]] || return 1
  return 0
}
