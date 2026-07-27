#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source "$script_dir/lib/env.sh"
# shellcheck disable=SC1091
source "$script_dir/lib/isaac-runtime.sh"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

report() {
  printf 'PASS: %s\n' "$*"
}

main() {
  local compose_env expected_owner path owner temp_probe
  load_lab_env
  require_docker
  require_docker_compose

  expected_owner="$(isaac_runtime_owner)"
  [[ "$(isaac_image_ref)" == "nvcr.io/nvidia/isaac-sim:6.0.1" ]] || \
    fail "Unexpected Isaac image reference: $(isaac_image_ref)"
  [[ "${ISAAC_SIM_UID}" == "1234" ]] || fail "Unexpected ISAAC_SIM_UID: ${ISAAC_SIM_UID}"
  [[ "${ISAAC_SIM_GID}" == "1234" ]] || fail "Unexpected ISAAC_SIM_GID: ${ISAAC_SIM_GID}"
  [[ "${PRIVACY_CONSENT}" == "N" ]] || fail "Unexpected PRIVACY_CONSENT: ${PRIVACY_CONSENT}"

  report "Compose identity: ${ISAAC_SIM_UID}:${ISAAC_SIM_GID}"

  while IFS= read -r path; do
    [[ -n "$path" ]] || continue
    [[ -e "$path" ]] || fail "Missing runtime path: $path"
    owner="$(stat -c '%u:%g' "$path")"
    [[ "$owner" == "$expected_owner" ]] || fail "Expected $path to be owned by $expected_owner, got $owner"
    temp_probe="$path/.ownership-probe.$$"
    if ! docker run --rm \
      --user 1234:1234 \
      -v "$path:$path:rw" \
      --entrypoint bash \
      "$(isaac_image_ref)" \
      -lc "set -euo pipefail; probe='$temp_probe'; : >\"\$probe\"; rm -f \"\$probe\""; then
      fail "Path is not writable by UID/GID 1234: $path"
    fi
    report "$path writable by 1234:1234"
  done < <(isaac_runtime_ownership_dirs)

  while IFS= read -r path; do
    [[ -n "$path" ]] || continue
    owner="$(stat -c '%u:%g' "$path")"
    printf 'INFO: %s ownership=%s\n' "$path" "$owner"
    if [[ "$owner" == "$expected_owner" ]]; then
      report "$path already owned by 1234:1234"
    fi
  done < <(isaac_runtime_data_dirs)
}

main "$@"
