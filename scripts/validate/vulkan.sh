vulkan_summary_has_nvidia_discrete_device() {
  local summary="$1"

  grep -Eiq 'deviceType[[:space:]]*=[[:space:]]*PHYSICAL_DEVICE_TYPE_DISCRETE_GPU' <<<"$summary" \
    && grep -Eiq 'deviceName[[:space:]]*=[[:space:]]*.*NVIDIA|driverName[[:space:]]*=[[:space:]]*NVIDIA|vendorName[[:space:]]*=[[:space:]]*NVIDIA' <<<"$summary"
}

vulkan_summary_has_software_renderer() {
  local summary="$1"

  grep -Eiq 'llvmpipe|software rasterizer|PHYSICAL_DEVICE_TYPE_CPU' <<<"$summary"
}

vulkan_summary_has_surface_info() {
  local summary="$1"

  grep -Eiq 'surface info:|DISPLAY = |WAYLAND_DISPLAY = ' <<<"$summary"
}

vulkan_summary_has_xcb_surface_failure() {
  local summary="$1"

  grep -Eiq 'XCB failed to connect to the X server|AppCreateXcbSurface failed to establish connection' <<<"$summary"
}

vulkan_summary_excerpt() {
  local summary="$1"

  printf '%s\n' "$summary" | sed -n '1,40p'
}

validate_vulkan() {
  validation_section "Vulkan"
  local start_failures="$VALIDATION_FAILURES"
  local status="PASS"
  local summary_output=""

  if ! command -v vulkaninfo >/dev/null 2>&1; then
    validation_warn "vulkaninfo is not installed"
    validation_set_readiness "Vulkan" "WARN" "vulkaninfo missing"
    return
  fi

  summary_output="$(env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY vulkaninfo --summary 2>&1 || true)"

  if [[ -z "$summary_output" ]]; then
    validation_fail "vulkaninfo produced no summary output"
    validation_set_readiness "Vulkan" "FAIL" "no summary output"
    return
  fi

  if vulkan_summary_has_nvidia_discrete_device "$summary_output"; then
    validation_pass "Detected NVIDIA discrete Vulkan device"
    if grep -Eiq 'deviceName[[:space:]]*=[[:space:]]*.*NVIDIA' <<<"$summary_output"; then
      validation_info "$(grep -Ei 'deviceName[[:space:]]*=[[:space:]]*.*NVIDIA' <<<"$summary_output" | head -n1)"
    fi
    if grep -Eiq 'driverName[[:space:]]*=[[:space:]]*NVIDIA' <<<"$summary_output"; then
      validation_info "$(grep -Ei 'driverName[[:space:]]*=[[:space:]]*NVIDIA' <<<"$summary_output" | head -n1)"
    fi
  elif vulkan_summary_has_software_renderer "$summary_output"; then
    validation_fail "Vulkan reports only software rendering"
    validation_set_readiness "Vulkan" "FAIL" "software renderer detected"
    validation_info "Vulkan summary excerpt:"
    while IFS= read -r line; do
      validation_info "  $line"
    done < <(vulkan_summary_excerpt "$summary_output")
    return
  else
    validation_fail "Vulkan summary could not be classified"
    validation_set_readiness "Vulkan" "FAIL" "unclassified summary"
    validation_info "Vulkan summary excerpt:"
    while IFS= read -r line; do
      validation_info "  $line"
    done < <(vulkan_summary_excerpt "$summary_output")
    return
  fi

  if [[ -z "${DISPLAY:-}" ]]; then
    validation_info "Surface validation skipped because DISPLAY is absent"
  else
    local surface_output=""
    surface_output="$(vulkaninfo --summary 2>&1 || true)"
    if vulkan_summary_has_surface_info "$surface_output"; then
      validation_pass "Local display surface information is available"
    elif vulkan_summary_has_xcb_surface_failure "$surface_output"; then
      validation_info "Local surface validation could not connect to the X server"
    else
      validation_info "Local surface validation was not available"
    fi
  fi

  if (( VALIDATION_FAILURES > start_failures )); then
    status="FAIL"
  fi

  validation_set_readiness "Vulkan" "$status"
}
