validate_isaac() {
  validation_section "Isaac"

  local image_ref compose_file

  image_ref="$(isaac_image_ref)"
  compose_file="$(compose_file_path)"

  validation_pass "Pinned Isaac Sim image reference: $image_ref"

  if [[ -f "$compose_file" ]]; then
    validation_pass "Canonical Compose file present: $compose_file"
  else
    validation_fail "Canonical Compose file is missing: $compose_file"
  fi

  if command -v docker >/dev/null 2>&1; then
    if docker image inspect "$image_ref" >/dev/null 2>&1; then
      validation_pass "Isaac Sim image present locally: $image_ref"
    else
      validation_warn "Isaac Sim image is not present locally: $image_ref"
    fi
  else
    validation_warn "Docker is unavailable; local image presence check skipped"
  fi
}
