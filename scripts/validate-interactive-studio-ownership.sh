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

interactive_studio_probe_container() {
  local user_spec="$1"
  local path="$2"
  local label="$3"
  local group_add="${4:-}"
  local image
  local -a docker_args=()

  image="$(interactive_studio_image_ref)"
  docker image inspect "$image" >/dev/null 2>&1 || fail "Pinned Interactive Studio image is not present locally: $image"

  docker_args=(run --pull=never --rm --user "$user_spec")
  if [[ -n "$group_add" ]]; then
    docker_args+=(--group-add "$group_add")
  fi
  docker_args+=(
    --entrypoint sh
    -v "$path:$path:rw"
    "$image"
    -eu
    -c
    'umask 0002; probe="$1/.interactive-studio-container-probe.$$"; : > "$probe"; rm -f "$probe"'
    sh
    "$path"
  )

  docker "${docker_args[@]}" >/dev/null
  printf 'PASS: %s probe succeeded: %s\n' "$label" "$path"
}

interactive_studio_probe_read_only_container() {
  local path="$1"
  local label="$2"
  local image
  local -a docker_args=()

  image="$(interactive_studio_image_ref)"
  docker image inspect "$image" >/dev/null 2>&1 || fail "Pinned Interactive Studio image is not present locally: $image"

  docker_args=(
    run
    --pull=never
    --rm
    --user 1234:1234
    --entrypoint sh
    -v "$path:$path:ro"
    "$image"
    -u
    -c
    '
      probe="$1/.interactive-studio-shared-assets-readonly-probe.$$"
      if touch "$probe" >/dev/null 2>&1; then
        rm -f "$probe"
        printf "FAIL: Shared Assets unexpectedly writable\n" >&2
        exit 1
      fi
      if [ -e "$probe" ]; then
        rm -f "$probe" || {
          printf "FAIL: Shared Assets probe cleanup failed\n" >&2
          exit 1
        }
      fi
      printf "PASS: Shared Assets are read-only\n"
      exit 0
    '
    sh
    "$path"
  )

  docker "${docker_args[@]}" >/dev/null
  printf 'PASS: %s remains read-only to the container user: %s\n' "$label" "$path"
}

interactive_studio_probe_host_workspace() {
  local path="$1"
  local probe="$2"

  : > "$probe"
  rm -f "$probe"
  printf 'PASS: host workspace probe succeeded: %s\n' "$path"
}

main() {
  local root path owner mode shared_owner shared_mode probe

  load_lab_env

  printf 'Validating Interactive Studio ownership policy\n'

  interactive_studio_validate_no_phase6_reuse || fail "Interactive Studio reuses a Phase 6 path"

  [[ "$(id -u)" == "1000" ]] || fail "Run the ownership validator as the approved host user 1000"
  [[ "$(id -g)" == "1000" ]] || fail "Run the ownership validator as the approved host group 1000"

  root="$(interactive_studio_root)"
  [[ -e "$root" ]] || fail "Missing Interactive Studio root: $root"
  [[ "$(stat -c '%a' "$root")" == "755" ]] || fail "Interactive Studio root mode mismatch: $root"
  [[ -x "$root" ]] || fail "Interactive Studio root is not traversable by the host user: $root"
  printf 'PASS: root traversal validated: %s\n' "$root"

  while IFS= read -r path; do
    [[ -n "$path" ]] || continue
    [[ -e "$path" ]] || fail "Missing runtime path: $path"
    if [[ "$path" == "$root" ]]; then
      continue
    fi
    owner="$(stat -c '%u:%g' "$path")"
    [[ "$owner" == "1234:1234" ]] || fail "Runtime path ownership mismatch: $path -> $owner"
    interactive_studio_probe_container "1234:1234" "$path" "runtime"
  done < <(interactive_studio_runtime_paths)

  while IFS= read -r path; do
    [[ -n "$path" ]] || continue
    [[ -e "$path" ]] || fail "Missing workspace path: $path"
    owner="$(stat -c '%u:%g' "$path")"
    mode="$(stat -c '%a' "$path")"
    [[ "$owner" == "1000:1000" ]] || fail "Workspace path ownership mismatch: $path -> $owner"
    [[ "$mode" == "2775" ]] || fail "Workspace path mode mismatch: $path -> $mode"
    probe="$path/.interactive-studio-host-workspace-probe.$$"
    interactive_studio_probe_host_workspace "$path" "$probe"
    interactive_studio_probe_container "1234:1234" "$path" "workspace" "$(interactive_studio_shared_gid)"
  done < <(interactive_studio_workspace_paths)

  while IFS= read -r path; do
    [[ -n "$path" ]] || continue
    [[ -e "$path" ]] || fail "Missing shared asset path: $path"
    shared_owner="$(stat -c '%u:%g' "$path")"
    shared_mode="$(stat -c '%a' "$path")"
    [[ "$shared_owner" != "1234:1234" ]] || fail "Shared asset path must not be owned by the container: $path"
    [[ "$shared_mode" =~ ^[0-7]+$ ]] || fail "Shared asset path mode is invalid: $path -> $shared_mode"
    interactive_studio_probe_read_only_container "$path" "shared assets"
  done < <(interactive_studio_shared_asset_paths)

  printf 'PASS: ownership policy validated\n'
}

main "$@"
