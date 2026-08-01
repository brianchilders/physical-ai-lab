#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source "$script_dir/lib/env.sh"
# shellcheck disable=SC1091
source "$script_dir/lib/physics-foundations.sh"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

report() {
  printf 'PASS: %s\n' "$*"
}

main() {
  local root
  local -a ownership_paths

  load_lab_env
  root="$(physics_foundations_runtime_root)"

  ownership_paths=(
    "$root/output"
    "$root/results"
    "$root/output/run-01"
    "$root/output/run-02"
    "$root/results/run-01"
    "$root/results/run-02"
    "$root/cache/main"
    "$root/cache/computecache"
    "$root/cache/hub"
    "$root/logs"
    "$root/config"
    "$root/data"
    "$root/pkg"
  )

  if ((${#ownership_paths[@]} == 0)); then
    fail 'No Phase 6 ownership paths were discovered'
  fi

  require_docker

  docker run --rm --pull=never \
    --user 1234:1234 \
    --entrypoint bash \
    -v /mnt/nvme/isaac:/mnt/nvme/isaac \
    nvcr.io/nvidia/isaac-sim:6.0.1 \
    -lc 'set -euo pipefail
expected_owner=1234:1234
for path in "$@"; do
  [[ -e "$path" ]] || { printf "FAIL: Missing required path: %s\n" "$path" >&2; exit 1; }
  owner="$(stat -c "%u:%g" "$path")"
  [[ "$owner" == "$expected_owner" ]] || { printf "FAIL: Expected %s to be owned by %s, got %s\n" "$path" "$expected_owner" "$owner" >&2; exit 1; }
  probe="$path/.ownership-write-check"
  : >"$probe"
      rm -f "$probe"
      printf "PASS: %s owned and writable by 1234:1234\n" "$path"
done' _ "${ownership_paths[@]}"
}

main "$@"
