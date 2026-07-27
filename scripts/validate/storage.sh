readonly STORAGE_ROOT="${ISAAC_STORAGE_ROOT:-/mnt/nvme/isaac}"

validate_storage() {
  validation_section "Storage"

  if [[ ! -d "$NVME_ROOT" ]]; then
    validation_fail "$NVME_ROOT does not exist"
    return
  fi

  if ! findmnt -rn "$NVME_ROOT" >/dev/null 2>&1; then
    validation_fail "$NVME_ROOT is not mounted"
    return
  fi

  validation_pass "$NVME_ROOT is mounted"
  df -h "$NVME_ROOT"

  local -a dirs=(
    "$ISAAC_STORAGE_ROOT"
    "$ISAAC_STORAGE_ROOT/cache"
    "$ISAAC_STORAGE_ROOT/cache/isaac-sim"
    "$ISAAC_STORAGE_ROOT/cache/isaac-sim/main"
    "$ISAAC_STORAGE_ROOT/cache/isaac-sim/computecache"
    "$ISAAC_STORAGE_ROOT/cache/ov"
    "$ISAAC_STORAGE_ROOT/cache/ov/hub"
    "$ISAAC_STORAGE_ROOT/assets"
    "$ISAAC_STORAGE_ROOT/datasets"
    "$ISAAC_STORAGE_ROOT/logs"
    "$ISAAC_STORAGE_ROOT/logs/isaac-sim"
    "$ISAAC_STORAGE_ROOT/projects"
    "$ISAAC_STORAGE_ROOT/projects/isaac-sim"
    "$ISAAC_STORAGE_ROOT/projects/isaac-sim/config"
    "$ISAAC_STORAGE_ROOT/projects/isaac-sim/data"
    "$ISAAC_STORAGE_ROOT/projects/isaac-sim/pkg"
  )

  local dir
  for dir in "${dirs[@]}"; do
    if [[ -d "$dir" ]]; then
      validation_pass "Directory present: $dir"
    else
      validation_fail "Missing directory: $dir"
    fi
  done
}
