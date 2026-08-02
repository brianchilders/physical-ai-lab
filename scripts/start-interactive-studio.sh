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
  local name image host_ip runtime_root workspace_root repo_root_path state container_id launch_command
  local -a docker_args=()
  local spec host_path container_path mode purpose

  load_lab_env
  require_docker

  name="$(interactive_studio_container_name)"
  image="$(interactive_studio_image_ref)"
  host_ip="$(interactive_studio_host_ip)"
  runtime_root="$(interactive_studio_root)"
  workspace_root="$(interactive_studio_workspace_root)"
  repo_root_path="$(interactive_studio_repo_root)"

  if ! interactive_studio_validate_host_ip "$host_ip"; then
    fail "Invalid INTERACTIVE_STUDIO_HOST_IP: ${host_ip:-<unset>}"
  fi

  if ! interactive_studio_validate_no_phase6_reuse; then
    fail "Interactive Studio paths must not reuse Phase 6 runtime roots"
  fi

  if ! interactive_studio_validate_mount_boundary; then
    fail "Interactive Studio mount boundary is invalid"
  fi

  if ! interactive_studio_validate_required_paths; then
    fail "Interactive Studio paths are missing. Run prepare-interactive-studio first."
  fi

  if ! interactive_studio_validate_port_availability; then
    fail "Interactive Studio streaming ports appear to be in use"
  fi

  if ! docker image inspect "$image" >/dev/null 2>&1; then
    fail "Pinned Interactive Studio image is not present locally: $image"
  fi

  state="$(interactive_studio_container_state)"
  case "$state" in
    running)
      report "Interactive Studio container already running: $name"
      report "Host IP: $host_ip"
      report "Signal port: $(interactive_studio_signal_port)"
      report "Stream port: $(interactive_studio_stream_port)"
      exit 0
      ;;
    stopped)
      fail "A stopped Interactive Studio container already exists: $name"
      ;;
  esac

  launch_command=$(printf 'set -euo pipefail; cd /isaac-sim; umask 0002; exec ./runheadless.sh -v --/exts/omni.kit.livestream.app/primaryStream/publicIp=%q --/exts/omni.kit.livestream.app/primaryStream/signalPort=%q --/exts/omni.kit.livestream.app/primaryStream/streamPort=%q' \
    "$host_ip" \
    "$(interactive_studio_signal_port)" \
    "$(interactive_studio_stream_port)")

  docker_args+=(
    run
    -d
    --pull=never
    --name "$name"
    --gpus all
    --network=host
    --shm-size=16g
    --user 1234:1234
    --group-add "$(interactive_studio_shared_gid)"
    --entrypoint bash
    -e ACCEPT_EULA=Y
    -e PRIVACY_CONSENT=N
    -w "$workspace_root"
  )

  while IFS='|' read -r host_path container_path mode purpose; do
    [[ -n "$host_path" ]] || continue
    docker_args+=(-v "$host_path:$container_path:$mode")
  done < <(interactive_studio_mount_specs)

  docker_args+=(
    "$image"
    -lc "$launch_command"
  )

  container_id="$(docker "${docker_args[@]}")"
  report "Interactive Studio container started: $container_id"
  report "Host IP: $host_ip"
  report "Signal port: $(interactive_studio_signal_port)"
  report "Stream port: $(interactive_studio_stream_port)"
  report "Launch handoff: exec ./runheadless.sh replaces the shell process"
  report "Use the Isaac Sim WebRTC Streaming Client on Windows to connect."
}

main "$@"
