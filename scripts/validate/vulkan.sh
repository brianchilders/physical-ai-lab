validate_vulkan() {
  validation_section "Vulkan"

  if ! command -v vulkaninfo >/dev/null 2>&1; then
    validation_warn "vulkaninfo is not installed"
    return
  fi

  if vulkaninfo --summary >/dev/null 2>&1; then
    validation_pass "Vulkan validation passed"
  else
    validation_fail "Vulkan validation failed"
  fi
}

