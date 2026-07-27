#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/.." && pwd)"

# shellcheck disable=SC1091
source "$repo_root/scripts/lib/env.sh"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

discover_shell_scripts() {
  (
    cd "$repo_root" && find . -type f -name '*.sh' -not -path './.git/*' | sort
  )
}

run_shellcheck() {
  if ! command -v shellcheck >/dev/null 2>&1; then
    printf 'SKIP: shellcheck is not installed\n'
    return 0
  fi

  mapfile -t sh_files < <(discover_shell_scripts)
  if ((${#sh_files[@]} == 0)); then
    printf 'SKIP: no shell scripts found\n'
    return 0
  fi

  shellcheck "${sh_files[@]/#/$repo_root/}"
}

run_bash_syntax() {
  mapfile -t sh_files < <(discover_shell_scripts)
  if ((${#sh_files[@]} == 0)); then
    fail 'No shell scripts found with portable find discovery'
  fi

  bash -n "${sh_files[@]/#/$repo_root/}"
}

run_config_check() {
  load_lab_env

  [[ "${ISAAC_SIM_REGISTRY}" == "nvcr.io" ]] || fail "Unexpected registry: ${ISAAC_SIM_REGISTRY}"
  [[ "${ISAAC_SIM_REPOSITORY}" == "nvidia/isaac-sim" ]] || fail "Unexpected repository: ${ISAAC_SIM_REPOSITORY}"
  [[ "${ISAAC_SIM_TAG}" == "6.0.1" ]] || fail "Unexpected tag: ${ISAAC_SIM_TAG}"
  [[ "${ISAAC_SIM_UID}" == "1234" ]] || fail "Unexpected ISAAC_SIM_UID: ${ISAAC_SIM_UID}"
  [[ "${ISAAC_SIM_GID}" == "1234" ]] || fail "Unexpected ISAAC_SIM_GID: ${ISAAC_SIM_GID}"
  [[ "${PRIVACY_CONSENT}" == "N" ]] || fail "Unexpected PRIVACY_CONSENT: ${PRIVACY_CONSENT}"

  local image_ref
  image_ref="$(isaac_image_ref)"
  [[ "$image_ref" == "nvcr.io/nvidia/isaac-sim:6.0.1" ]] || fail "Unexpected image ref: $image_ref"

  (
    export ISAAC_SIM_TAG=9.9.9
    load_lab_env
    [[ "$ISAAC_SIM_TAG" == "9.9.9" ]] || fail "Shell environment did not win precedence"
  )

  grep -n -E '^ISAAC_STORAGE_ROOT=' "$repo_root/.env.example" >/dev/null 2>&1 && \
    fail '.env.example should not define ISAAC_STORAGE_ROOT'
  grep -n -E '^ISAAC_SIM_(REGISTRY|REPOSITORY|TAG)=' "$repo_root/.env.example" >/dev/null 2>&1 && \
    fail '.env.example should not define pinned Isaac Sim image variables'
  grep -n -E '^ISAAC_SIM_UID=1234$' "$repo_root/.env.example" >/dev/null 2>&1 || \
    fail '.env.example should set ISAAC_SIM_UID to 1234'
  grep -n -E '^ISAAC_SIM_GID=1234$' "$repo_root/.env.example" >/dev/null 2>&1 || \
    fail '.env.example should set ISAAC_SIM_GID to 1234'
  grep -n -E '^PRIVACY_CONSENT=N$' "$repo_root/.env.example" >/dev/null 2>&1 || \
    fail '.env.example should default PRIVACY_CONSENT to N'
  grep -n -E '^(DISPLAY|XAUTHORITY)=' "$repo_root/.env.example" >/dev/null 2>&1 && \
    fail '.env.example should not define GUI session defaults'

  [[ -f "$repo_root/config/lab.env.example" ]] || fail "Missing config/lab.env.example"
  [[ -f "$repo_root/.env.example" ]] || fail "Missing .env.example"

  if grep -R -n -E '/mnt/nvme/(cache|assets|datasets|logs|projects)' \
    "$repo_root/docker/isaac/compose.yaml" \
    "$repo_root/docs" \
    "$repo_root/assets/README.md" \
    "$repo_root/datasets/README.md" \
    "$repo_root/launch-headless.sh" \
    "$repo_root/launch-gui.sh" \
    "$repo_root/prepare-storage.sh" \
    "$repo_root/scripts" \
    "$repo_root/stop.sh" >/dev/null 2>&1; then
    fail 'Found forbidden alternate storage paths under /mnt/nvme/* outside isaac/'
  fi
}

run_compose_check() {
  load_lab_env
  require_docker
  require_docker_compose
  local compose_env output_file
  compose_env="$(mktemp)"
  output_file="$(mktemp)"
  trap 'rm -f "${compose_env:-}" "${output_file:-}"' EXIT
  write_compose_env_file "$compose_env"

  docker compose \
    --env-file "$compose_env" \
    --file "$repo_root/docker/isaac/compose.yaml" \
    --profile headless \
    config >"$output_file"

  grep -n -E '^    user: 1234:1234$' "$output_file" >/dev/null 2>&1 || \
    fail 'Headless compose render did not resolve the supported 1234:1234 user'
  if grep -n -E '1000:1000' "$output_file" >/dev/null 2>&1; then
    fail 'Headless compose render still references 1000:1000'
  fi
}

run_gui_compose_check() {
  load_lab_env
  require_docker
  require_docker_compose
  local compose_env xauth_file output_file
  compose_env="$(mktemp)"
  xauth_file="$(mktemp)"
  output_file="$(mktemp)"
  trap 'rm -f "${compose_env:-}" "${xauth_file:-}" "${output_file:-}"' EXIT
  : >"$xauth_file"
  export DISPLAY=':99'
  export XAUTHORITY="$xauth_file"
  write_gui_compose_env_file "$compose_env"

  docker compose \
    --env-file "$compose_env" \
    --file "$repo_root/docker/isaac/compose.yaml" \
    --file "$repo_root/docker/isaac/compose.gui.yaml" \
    --profile gui \
    config >"$output_file"

  grep -n -E 'target: /isaac-sim/\.Xauthority' "$output_file" >/dev/null 2>&1 || \
    fail 'GUI compose render did not include the Xauthority mount'
  grep -n -E 'source: /tmp/' "$output_file" >/dev/null 2>&1 || \
    fail 'GUI compose render did not use a real temporary Xauthority file'
  grep -n -E '^    user: 1234:1234$' "$output_file" >/dev/null 2>&1 || \
    fail 'GUI compose render did not resolve the supported 1234:1234 user'
  if grep -n -E '(:0|/home/[^/]+/\.Xauthority)' "$output_file" >/dev/null 2>&1; then
    fail 'GUI compose render injected a fake DISPLAY or default Xauthority path'
  fi
}

run_gui_guard_checks() {
  local output_file
  output_file="$(mktemp)"
  trap 'rm -f "${output_file:-}"' RETURN

  if env -u DISPLAY -u XAUTHORITY bash "$repo_root/launch-gui.sh" >"$output_file" 2>&1; then
    fail 'launch-gui.sh succeeded without DISPLAY and XAUTHORITY'
  fi
  grep -n -E 'DISPLAY is not set' "$output_file" >/dev/null 2>&1 || \
    fail 'launch-gui.sh did not reject missing DISPLAY'

  if env DISPLAY=':99' XAUTHORITY=/tmp/does-not-exist bash "$repo_root/launch-gui.sh" >"$output_file" 2>&1; then
    fail 'launch-gui.sh succeeded with a missing XAUTHORITY file'
  fi
  grep -n -E 'XAUTHORITY is not available' "$output_file" >/dev/null 2>&1 || \
    fail 'launch-gui.sh did not reject missing or nonexistent XAUTHORITY'
}

create_stop_docker_stub() {
  local stub_dir="$1"

  cat >"$stub_dir/bin/docker" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

log_file="${DOCKER_STUB_LOG_FILE:?unset DOCKER_STUB_LOG_FILE}"
subcommand="${1:-}"
shift || true

case "$subcommand" in
  compose)
    if [[ "${1:-}" == "version" ]]; then
      printf 'compose version\n' >>"$log_file"
      printf '%s\n' "${DOCKER_STUB_COMPOSE_VERSION:-Docker Compose version v2.99.0}"
      exit 0
    fi

    printf 'compose %s\n' "$*" >>"$log_file"
    env_file=""
    args=("$@")
    for ((i=0; i<${#args[@]}; i++)); do
      if [[ "${args[i]}" == "--env-file" ]]; then
        env_file="${args[i+1]:-}"
      fi
    done

    if [[ -n "$env_file" ]]; then
      printf 'env-file:%s\n' "$env_file" >>"$log_file"
      while IFS= read -r line; do
        printf 'env:%s\n' "$line" >>"$log_file"
      done <"$env_file"
    fi
    exit 0
    ;;
  ps)
    printf 'ps %s\n' "$*" >>"$log_file"
    if [[ -n "${DOCKER_STUB_PS_OUTPUT:-}" ]]; then
      printf '%s\n' "$DOCKER_STUB_PS_OUTPUT"
    fi
    exit 0
    ;;
esac

printf 'unexpected %s %s\n' "$subcommand" "$*" >>"$log_file"
exit 1
EOF
  chmod +x "$stub_dir/bin/docker"
}

run_env_helper_idempotency_check() {
  local output_file
  output_file="$(mktemp)"
  trap 'rm -f "${output_file:-}"' RETURN

  if ! bash -lc "set -euo pipefail; cd '$repo_root'; source scripts/lib/env.sh; source scripts/lib/env.sh; load_lab_env; printf 'OK\n'" >"$output_file" 2>&1; then
    cat "$output_file" >&2
    fail 'scripts/lib/env.sh could not be sourced twice in the same shell'
  fi

  grep -n -x 'OK' "$output_file" >/dev/null 2>&1 || \
    fail 'env.sh double-source check did not complete cleanly'
  if grep -n -E 'LAB_ENV_VARS: readonly variable' "$output_file" >/dev/null 2>&1; then
    fail 'env.sh still emits readonly-variable errors on repeated sourcing'
  fi
}

run_stop_lifecycle_checks() {
  local success_stub_dir success_output_file success_compose_log
  local failure_stub_dir failure_output_file failure_compose_log

  success_stub_dir="$(mktemp -d)"
  success_output_file="$(mktemp)"
  success_compose_log="$success_stub_dir/compose.log"
  mkdir -p "$success_stub_dir/bin"
  create_stop_docker_stub "$success_stub_dir"

  env -u DISPLAY -u XAUTHORITY \
    PATH="$success_stub_dir/bin:$PATH" \
    DOCKER_STUB_LOG_FILE="$success_compose_log" \
    bash "$repo_root/stop.sh" >"$success_output_file" 2>&1

  grep -n -E '^compose version$' "$success_compose_log" >/dev/null 2>&1 || \
    fail 'stop.sh did not verify Docker Compose availability'
  grep -n -E '^compose --env-file .* --file .*/docker/isaac/compose\.yaml --profile headless -p isaac down --remove-orphans$' \
    "$success_compose_log" >/dev/null 2>&1 || \
    fail 'stop.sh did not use the headless profile, isaac project, and base compose file'
  grep -n -E '^ps -a --filter label=com\.docker\.compose\.project=isaac --format \{\{\.Names\}\}$' \
    "$success_compose_log" >/dev/null 2>&1 || \
    fail 'stop.sh did not verify Docker project labels after Compose returned'
  if grep -n -E '^env:(DISPLAY|XAUTHORITY)=' "$success_compose_log" >/dev/null 2>&1; then
    fail 'stop.sh still writes DISPLAY or XAUTHORITY into the Compose env file'
  fi
  if grep -n -E 'prune|docker rmi|docker image rm|docker volume rm|rm -rf|/mnt/nvme/isaac' \
    "$repo_root/stop.sh" >/dev/null 2>&1; then
    fail 'stop.sh contains forbidden prune, deletion, or persistent-data removal commands'
  fi

  failure_stub_dir="$(mktemp -d)"
  failure_output_file="$(mktemp)"
  failure_compose_log="$failure_stub_dir/compose.log"
  mkdir -p "$failure_stub_dir/bin"
  create_stop_docker_stub "$failure_stub_dir"
  if env -u DISPLAY -u XAUTHORITY \
    PATH="$failure_stub_dir/bin:$PATH" \
    DOCKER_STUB_LOG_FILE="$failure_compose_log" \
    DOCKER_STUB_PS_OUTPUT='isaac-sim-headless' \
    bash "$repo_root/stop.sh" >"$failure_output_file" 2>&1; then
    fail 'stop.sh succeeded even though isaac project containers remained'
  fi
  grep -n -E 'Compose project isaac still has containers' "$failure_output_file" >/dev/null 2>&1 || \
    fail 'stop.sh did not fail with a lingering isaac project container'

  rm -rf "$success_stub_dir" "$failure_stub_dir"
  rm -f "$success_output_file" "$failure_output_file"
}

run_headless_launch_path_checks() {
  if grep -n -E '\.write-check|require_writable_dir' "$repo_root/launch-headless.sh" >/dev/null 2>&1; then
    fail 'launch-headless.sh still performs host-side write probes'
  fi

  if ! grep -n -E '\./scripts/validate-runtime-ownership\.sh' "$repo_root/launch-headless.sh" >/dev/null 2>&1; then
    fail 'launch-headless.sh does not delegate to runtime ownership validation'
  fi
}

run_ownership_path_checks() {
  local actual_paths expected_paths actual_data_paths expected_data_paths
  local actual_smoke_paths expected_smoke_paths

  # shellcheck disable=SC1091
  source "$repo_root/scripts/lib/isaac-runtime.sh"
  load_lab_env

  actual_paths="$(isaac_runtime_ownership_dirs)"
  expected_paths="$(
    printf '%s\n' \
      "$ISAAC_STORAGE_ROOT/cache/isaac-sim/main" \
      "$ISAAC_STORAGE_ROOT/cache/isaac-sim/computecache" \
      "$ISAAC_STORAGE_ROOT/cache/ov/hub" \
      "$ISAAC_STORAGE_ROOT/logs/isaac-sim" \
      "$ISAAC_STORAGE_ROOT/projects/isaac-sim/config" \
      "$ISAAC_STORAGE_ROOT/projects/isaac-sim/data" \
      "$ISAAC_STORAGE_ROOT/projects/isaac-sim/pkg"
  )"
  [[ "$actual_paths" == "$expected_paths" ]] || fail "Approved ownership path list changed unexpectedly"

  actual_data_paths="$(isaac_runtime_data_dirs)"
  expected_data_paths="$(
    printf '%s\n' \
      "$ISAAC_STORAGE_ROOT/assets" \
      "$ISAAC_STORAGE_ROOT/datasets"
  )"
  [[ "$actual_data_paths" == "$expected_data_paths" ]] || fail "Approved data path list changed unexpectedly"

  actual_smoke_paths="$(isaac_smoke_runtime_ownership_dirs)"
  expected_smoke_paths="$(
    printf '%s\n' \
      "$(isaac_smoke_runtime_root)/cache/main" \
      "$(isaac_smoke_runtime_root)/cache/computecache" \
      "$(isaac_smoke_runtime_root)/cache/hub" \
      "$(isaac_smoke_runtime_root)/logs" \
      "$(isaac_smoke_runtime_root)/config" \
      "$(isaac_smoke_runtime_root)/data" \
      "$(isaac_smoke_runtime_root)/pkg"
  )"
  [[ "$actual_smoke_paths" == "$expected_smoke_paths" ]] || fail "Approved smoke ownership path list changed unexpectedly"
}

run_ownership_guard_checks() {
  local output_file
  output_file="$(mktemp)"
  trap 'rm -f "${output_file:-}"' RETURN

  if make -s -C "$repo_root" prepare-runtime-ownership >"$output_file" 2>&1; then
    fail 'prepare-runtime-ownership succeeded without CONFIRM_CHOWN=1'
  fi

  grep -n -E 'CONFIRM_CHOWN=1' "$output_file" >/dev/null 2>&1 || \
    fail 'prepare-runtime-ownership guard did not mention CONFIRM_CHOWN=1'

  if grep -R -n -E 'chown -R|/mnt/nvme/docker-data|/mnt/nvme/isaac/|1000:1000' \
    "$repo_root/scripts/prepare-runtime-ownership.sh" \
    "$repo_root/scripts/validate-runtime-ownership.sh" \
    "$repo_root/scripts/prepare-smoke-runtime-ownership.sh" \
    "$repo_root/scripts/validate-smoke-runtime-ownership.sh" \
    "$repo_root/Makefile" >/dev/null 2>&1; then
    fail 'Ownership helpers target a broad path, docker-data, or the wrong UID/GID'
  fi

  if ! grep -n -E 'chown 1234:1234' "$repo_root/scripts/prepare-runtime-ownership.sh" >/dev/null 2>&1; then
    fail 'prepare-runtime-ownership does not target the supported 1234:1234 identity'
  fi
  if ! grep -n -E 'chown 1234:1234' "$repo_root/scripts/prepare-smoke-runtime-ownership.sh" >/dev/null 2>&1; then
    fail 'prepare-smoke-runtime-ownership does not target the supported 1234:1234 identity'
  fi
}

run_validate_ownership_script_checks() {
  if ! grep -n -E -- '--user 1234:1234' "$repo_root/scripts/validate-runtime-ownership.sh" >/dev/null 2>&1; then
    fail 'validate-runtime-ownership does not probe with the supported 1234:1234 identity'
  fi
  if ! grep -n -E 'isaac_runtime_ownership_dirs|isaac_runtime_data_dirs' "$repo_root/scripts/validate-runtime-ownership.sh" >/dev/null 2>&1; then
    fail 'validate-runtime-ownership is not using the approved runtime path lists'
  fi
  if ! grep -n -E -- '--user 1234:1234' "$repo_root/scripts/validate-smoke-runtime-ownership.sh" >/dev/null 2>&1; then
    fail 'validate-smoke-runtime-ownership does not probe with the supported 1234:1234 identity'
  fi
  if ! grep -n -E 'isaac_smoke_runtime_ownership_dirs' "$repo_root/scripts/validate-smoke-runtime-ownership.sh" >/dev/null 2>&1; then
    fail 'validate-smoke-runtime-ownership is not using the approved smoke runtime path list'
  fi
}

run_image_status() {
  load_lab_env
  require_docker
  local image_ref
  image_ref="$(isaac_image_ref)"
  if docker image inspect "$image_ref" >/dev/null 2>&1; then
    printf 'PASS: Image present locally: %s\n' "$image_ref"
  else
    printf 'WARN: Image not present locally: %s\n' "$image_ref"
  fi
}

run_pull_image_guard_check() {
  local output_file
  output_file="$(mktemp)"
  trap 'rm -f "${output_file:-}"' RETURN

  if make -s -C "$repo_root" pull-image >"$output_file" 2>&1; then
    fail 'pull-image succeeded without CONFIRM_PULL=1'
  fi

  grep -n -E 'CONFIRM_PULL=1' "$output_file" >/dev/null 2>&1 || \
    fail 'pull-image guard message did not mention CONFIRM_PULL=1'
  grep -n -E 'nvcr.io/nvidia/isaac-sim:6.0.1' "$output_file" >/dev/null 2>&1 || \
    fail 'pull-image guard output did not preserve the pinned image reference'
}

run_pull_image_preview_check() {
  local output_file
  output_file="$(mktemp)"
  trap 'rm -f "${output_file:-}"' RETURN

  make -s -n -C "$repo_root" pull-image CONFIRM_PULL=1 >"$output_file" 2>&1

  grep -n -E '^docker pull nvcr\.io/nvidia/isaac-sim:6\.0\.1$' "$output_file" >/dev/null 2>&1 || \
    fail 'pull-image dry run did not resolve only the pinned Isaac Sim image'

  if grep -n -E 'docker login|docker run|docker compose up|prune|latest' "$output_file" >/dev/null 2>&1; then
    fail 'pull-image dry run included forbidden login, launch, prune, or latest usage'
  fi
}

run_fixture_tests() {
  "$repo_root/tests/validation-fixtures.sh" all
}

run_policy_check() {
  if grep -R -n -E 'docker login' \
    "$repo_root/launch-headless.sh" \
    "$repo_root/launch-gui.sh" \
    "$repo_root/stop.sh" \
    "$repo_root/Makefile" \
    "$repo_root/docker/isaac/compose.yaml" >/dev/null 2>&1; then
    fail 'Found forbidden automatic pull/login commands'
  fi

  if grep -n -E 'docker compose up|docker run|prune|latest' "$repo_root/Makefile" >/dev/null 2>&1; then
    fail 'Makefile contains forbidden launch, prune, or latest usage in the guarded pull path'
  fi

  if grep -R -n -E 'chown -R|/mnt/nvme/docker-data|1000:1000' \
    "$repo_root/scripts/prepare-runtime-ownership.sh" \
    "$repo_root/scripts/validate-runtime-ownership.sh" \
    "$repo_root/scripts/lib/isaac-runtime.sh" >/dev/null 2>&1; then
    fail 'Ownership helpers include a broad chown target, docker-data, or the wrong UID/GID'
  fi

  if grep -R -n -E 'chown -R|/mnt/nvme/docker-data|1000:1000' \
    "$repo_root/scripts/prepare-smoke-runtime-ownership.sh" \
    "$repo_root/scripts/validate-smoke-runtime-ownership.sh" \
    "$repo_root/scripts/lib/isaac-runtime.sh" >/dev/null 2>&1; then
    fail 'Smoke ownership helpers include a broad chown target, docker-data, or the wrong UID/GID'
  fi

  if grep -n -E '\.Xauthority' "$repo_root/launch-headless.sh" "$repo_root/docker/isaac/compose.yaml" >/dev/null 2>&1; then
    fail 'Headless launch path still references .Xauthority'
  fi

  if grep -n -E '(:0|/home/[^/]+/\.Xauthority)' "$repo_root/docker/isaac/compose.gui.yaml" >/dev/null 2>&1; then
    fail 'GUI override injects a fake DISPLAY or default Xauthority path'
  fi

  if grep -n -E 'privileged:' "$repo_root/docker/isaac/compose.yaml" >/dev/null 2>&1; then
    fail 'Found privileged container setting'
  fi

  if grep -n -E '/var/run/docker.sock' "$repo_root/docker/isaac/compose.yaml" >/dev/null 2>&1; then
    fail 'Found Docker socket mount'
  fi

  if grep -R -n -E 'docker run' "$repo_root/launch-headless.sh" "$repo_root/launch-gui.sh" "$repo_root/stop.sh" >/dev/null 2>&1; then
    fail 'Launch wrappers still contain docker run'
  fi

  if ! grep -n -E -- '--pull=never' "$repo_root/scripts/validate/docker.sh" >/dev/null 2>&1; then
    fail 'Docker GPU validator does not explicitly disable image pulling'
  fi

  if grep -R -n -E 'mkdir -p|rm -rf|chown|chmod|tee|apt-get|systemctl' "$repo_root/scripts/validate" >/dev/null 2>&1; then
    fail 'Validation scripts contain mutating commands'
  fi

  if grep -n -E 'prune|docker rmi|docker image rm|docker volume rm|rm -rf|/mnt/nvme/isaac' "$repo_root/stop.sh" >/dev/null 2>&1; then
    fail 'stop.sh contains forbidden prune, deletion, or persistent-data removal commands'
  fi
}

main() {
  local mode="${1:-all}"

  case "$mode" in
    all)
      run_bash_syntax
      run_policy_check
      run_config_check
      run_compose_check
      run_gui_compose_check
      run_image_status
      run_env_helper_idempotency_check
      run_stop_lifecycle_checks
      run_pull_image_guard_check
      run_pull_image_preview_check
      run_gui_guard_checks
      run_headless_launch_path_checks
      run_ownership_path_checks
      run_ownership_guard_checks
      run_validate_ownership_script_checks
      run_fixture_tests
      run_shellcheck
      ;;
    bash-syntax) run_bash_syntax ;;
    policy-check) run_policy_check ;;
    config-check) run_config_check ;;
    compose-check) run_compose_check ;;
    gui-compose-check) run_gui_compose_check ;;
    image-status) run_image_status ;;
    pull-image-check)
      run_pull_image_guard_check
      run_pull_image_preview_check
      ;;
    gui-guard-checks) run_gui_guard_checks ;;
    env-helper-idempotency-check) run_env_helper_idempotency_check ;;
    stop-lifecycle-checks) run_stop_lifecycle_checks ;;
    headless-launch-path-checks) run_headless_launch_path_checks ;;
    ownership-path-checks) run_ownership_path_checks ;;
    ownership-guard-checks) run_ownership_guard_checks ;;
    validate-ownership-script-checks) run_validate_ownership_script_checks ;;
    fixture-tests) run_fixture_tests ;;
    shellcheck) run_shellcheck ;;
    *)
      fail "Unknown mode: $mode"
      ;;
  esac
}

main "$@"
