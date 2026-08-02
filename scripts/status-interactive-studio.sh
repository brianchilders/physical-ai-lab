#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source "$script_dir/lib/env.sh"
# shellcheck disable=SC1091
source "$script_dir/lib/interactive-studio.sh"

main() {
  local name state marker logs tcp_ready udp_ready

  load_lab_env
  require_docker

  name="$(interactive_studio_container_name)"
  state="$(interactive_studio_container_state)"

  printf 'Interactive Studio status: %s\n' "$state"
  printf 'Container name: %s\n' "$name"
  printf 'Host IP: %s\n' "$(interactive_studio_host_ip)"
  printf 'Signal port: %s\n' "$(interactive_studio_signal_port)"
  printf 'Stream port: %s\n' "$(interactive_studio_stream_port)"

  case "$state" in
    running)
      if docker exec "$name" pgrep -fa 'isaac|kit|runheadless' >/dev/null 2>&1; then
        printf 'Isaac Sim process: detected\n'
      else
        printf 'Isaac Sim process: unknown\n'
      fi

      if logs="$(docker logs --tail 200 "$name" 2>/dev/null)"; then
        marker="unknown"
        while IFS= read -r candidate; do
          [[ -n "$candidate" ]] || continue
          if grep -Fq "$candidate" <<<"$logs"; then
            marker="$candidate"
            break
          fi
        done < <(interactive_studio_readiness_markers)
        if [[ "$marker" == "unknown" ]]; then
          printf 'Kit readiness: unknown\n'
          printf 'Kit readiness detail: candidate markers not yet observed\n'
        else
          printf 'Kit readiness: candidate marker -- pending validation against the pinned container logs: %s\n' "$marker"
        fi
      else
        printf 'Kit readiness: unknown\n'
        printf 'Kit readiness detail: logs unavailable\n'
      fi

      if ss -H -ltn "sport = :$(interactive_studio_signal_port)" | grep -q .; then
        tcp_ready="yes"
      else
        tcp_ready="unknown"
      fi
      if ss -H -lun "sport = :$(interactive_studio_stream_port)" | grep -q .; then
        udp_ready="yes"
      else
        udp_ready="unknown"
      fi
      if [[ "$tcp_ready" == "yes" || "$udp_ready" == "yes" ]]; then
        printf 'Streaming readiness: partial\n'
      else
        printf 'Streaming readiness: unknown\n'
      fi
      printf 'Streaming readiness detail: tcp=%s udp=%s\n' "$tcp_ready" "$udp_ready"
      printf 'Client connection: not observable\n'
      ;;
    stopped)
      printf 'Interactive Studio container exists but is stopped\n'
      printf 'Isaac Sim process: unknown\n'
      printf 'Kit readiness: not ready\n'
      printf 'Streaming readiness: not ready\n'
      printf 'Client connection: not connected\n'
      ;;
    absent)
      printf 'Interactive Studio container absent\n'
      printf 'Isaac Sim process: unknown\n'
      printf 'Kit readiness: not ready\n'
      printf 'Streaming readiness: not ready\n'
      printf 'Client connection: not connected\n'
      ;;
  esac
}

main "$@"
