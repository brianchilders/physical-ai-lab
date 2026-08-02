#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/.." && pwd)"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

check_present() {
  local needle="$1"
  local file="$2"
  grep -n -F -e "$needle" "$file" >/dev/null 2>&1 || fail "missing '$needle' in $file"
}

check_not_present() {
  local needle="$1"
  local file="$2"
  if grep -n -F -e "$needle" "$file" >/dev/null 2>&1; then
    fail "forbidden '$needle' found in $file"
  fi
}

check_make_target() {
  local target="$1"
  grep -n -E "^${target}:" "$repo_root/Makefile" >/dev/null 2>&1 || fail "missing Makefile target: $target"
}

main() {
  local file

  for file in \
    "$repo_root/scripts/lib/interactive-studio.sh" \
    "$repo_root/scripts/prepare-interactive-studio.sh" \
    "$repo_root/scripts/prepare-interactive-studio-ownership.sh" \
    "$repo_root/scripts/validate-interactive-studio-ownership.sh" \
    "$repo_root/scripts/start-interactive-studio.sh" \
    "$repo_root/scripts/stop-interactive-studio.sh" \
    "$repo_root/scripts/restart-interactive-studio.sh" \
    "$repo_root/scripts/status-interactive-studio.sh" \
    "$repo_root/scripts/logs-interactive-studio.sh" \
    "$repo_root/scripts/shell-interactive-studio.sh" \
    "$repo_root/scripts/validate-interactive-studio.sh" \
    "$repo_root/tests/phase7-refinement.sh"
  do
    [[ -f "$file" ]] || fail "missing expected file: $file"
  done

  check_present '/mnt/nvme/isaac/interactive-studio' "$repo_root/scripts/lib/interactive-studio.sh"
  check_present 'interactive-studio' "$repo_root/scripts/lib/interactive-studio.sh"
  check_present 'nvcr.io/nvidia/isaac-sim:6.0.1' "$repo_root/scripts/lib/interactive-studio.sh"
  check_present '49100' "$repo_root/scripts/lib/interactive-studio.sh"
  check_present '47998' "$repo_root/scripts/lib/interactive-studio.sh"
  check_present '/workspace/repo' "$repo_root/scripts/lib/interactive-studio.sh"
  check_present '/mnt/nvme/isaac/assets' "$repo_root/scripts/lib/interactive-studio.sh"
  check_present '/isaac-sim/.cache' "$repo_root/scripts/lib/interactive-studio.sh"
  check_present '/isaac-sim/.nv/ComputeCache' "$repo_root/scripts/lib/interactive-studio.sh"
  check_present '/isaac-sim/.nvidia-omniverse/config' "$repo_root/scripts/lib/interactive-studio.sh"
  check_present '/isaac-sim/.local/share/ov/data' "$repo_root/scripts/lib/interactive-studio.sh"
  check_present '/isaac-sim/.nvidia-omniverse/logs' "$repo_root/scripts/lib/interactive-studio.sh"
  check_present '/isaac-sim/.local/share/ov/pkg' "$repo_root/scripts/lib/interactive-studio.sh"
  check_present 'INTERACTIVE_STUDIO_HOST_IP' "$repo_root/scripts/lib/interactive-studio.sh"
  check_present 'interactive_studio_validate_host_ip' "$repo_root/scripts/lib/interactive-studio.sh"
  check_present 'interactive_studio_validate_no_phase6_reuse' "$repo_root/scripts/lib/interactive-studio.sh"
  check_present 'interactive_studio_validate_mount_boundary' "$repo_root/scripts/lib/interactive-studio.sh"
  check_present 'interactive_studio_readiness_markers' "$repo_root/scripts/lib/interactive-studio.sh"
  check_present 'interactive_studio_workspace_umask' "$repo_root/scripts/lib/interactive-studio.sh"
  check_present 'interactive_studio_runtime_paths' "$repo_root/scripts/lib/interactive-studio.sh"
  check_present 'interactive_studio_workspace_paths' "$repo_root/scripts/lib/interactive-studio.sh"
  check_present 'interactive_studio_shared_asset_paths' "$repo_root/scripts/lib/interactive-studio.sh"
  check_present '$repo_root_path|/workspace/repo|ro|repository' "$repo_root/scripts/lib/interactive-studio.sh"
  check_present '$assets_root|$assets_root|ro|shared_assets' "$repo_root/scripts/lib/interactive-studio.sh"
  check_present '$runtime_root/cache/main|/isaac-sim/.cache|rw|runtime_cache_main' "$repo_root/scripts/lib/interactive-studio.sh"
  check_present '$runtime_root/cache/computecache|/isaac-sim/.nv/ComputeCache|rw|runtime_cache_compute' "$repo_root/scripts/lib/interactive-studio.sh"
  check_present '$runtime_root/cache/hub|/var/cache/hub|rw|runtime_cache_hub' "$repo_root/scripts/lib/interactive-studio.sh"
  check_present '$runtime_root/config|/isaac-sim/.nvidia-omniverse/config|rw|runtime_config' "$repo_root/scripts/lib/interactive-studio.sh"
  check_present '$runtime_root/data|/isaac-sim/.local/share/ov/data|rw|runtime_data' "$repo_root/scripts/lib/interactive-studio.sh"
  check_present '$runtime_root/logs|/isaac-sim/.nvidia-omniverse/logs|rw|runtime_logs' "$repo_root/scripts/lib/interactive-studio.sh"
  check_present '$runtime_root/pkg|/isaac-sim/.local/share/ov/pkg|rw|runtime_pkg' "$repo_root/scripts/lib/interactive-studio.sh"
  check_present '$workspace_root|$workspace_root|rw|interactive_workspace' "$repo_root/scripts/lib/interactive-studio.sh"
  check_not_present 'PHYSICS_FOUNDATIONS_RUNTIME_ROOT' "$repo_root/scripts/lib/interactive-studio.sh"
  check_not_present 'os._exit()' "$repo_root/scripts/lib/interactive-studio.sh"

  check_present '--pull=never' "$repo_root/scripts/start-interactive-studio.sh"
  check_present '--name "$name"' "$repo_root/scripts/start-interactive-studio.sh"
  check_present '--gpus all' "$repo_root/scripts/start-interactive-studio.sh"
  check_present '--network=host' "$repo_root/scripts/start-interactive-studio.sh"
  check_present '--shm-size=16g' "$repo_root/scripts/start-interactive-studio.sh"
  check_present '--user 1234:1234' "$repo_root/scripts/start-interactive-studio.sh"
  check_present '--group-add' "$repo_root/scripts/start-interactive-studio.sh"
  check_present '--entrypoint bash' "$repo_root/scripts/start-interactive-studio.sh"
  check_present '-e ACCEPT_EULA=Y' "$repo_root/scripts/start-interactive-studio.sh"
  check_present '-e PRIVACY_CONSENT=N' "$repo_root/scripts/start-interactive-studio.sh"
  check_present 'primaryStream/publicIp=' "$repo_root/scripts/start-interactive-studio.sh"
  check_present 'primaryStream/signalPort=' "$repo_root/scripts/start-interactive-studio.sh"
  check_present 'primaryStream/streamPort=' "$repo_root/scripts/start-interactive-studio.sh"
  check_present 'exec ./runheadless.sh -v' "$repo_root/scripts/start-interactive-studio.sh"
  check_present 'umask 0002' "$repo_root/scripts/start-interactive-studio.sh"
  check_present 'interactive_studio_mount_specs' "$repo_root/scripts/start-interactive-studio.sh"
  check_present 'runheadless.sh -v' "$repo_root/scripts/start-interactive-studio.sh"
  check_present 'Invalid INTERACTIVE_STUDIO_HOST_IP' "$repo_root/scripts/start-interactive-studio.sh"
  check_present 'A stopped Interactive Studio container already exists' "$repo_root/scripts/start-interactive-studio.sh"
  check_present 'interactive_studio_validate_port_availability' "$repo_root/scripts/start-interactive-studio.sh"
  check_present 'interactive_studio_validate_required_paths' "$repo_root/scripts/start-interactive-studio.sh"
  check_present 'interactive_studio_validate_no_phase6_reuse' "$repo_root/scripts/start-interactive-studio.sh"
  check_not_present 'ISAACSIM_HOST' "$repo_root/scripts/start-interactive-studio.sh"
  check_not_present 'ISAACSIM_SIGNAL_PORT' "$repo_root/scripts/start-interactive-studio.sh"
  check_not_present 'ISAACSIM_STREAM_PORT' "$repo_root/scripts/start-interactive-studio.sh"
  check_not_present '--rm' "$repo_root/scripts/start-interactive-studio.sh"
  check_not_present '--restart' "$repo_root/scripts/start-interactive-studio.sh"
  check_not_present 'docker pull' "$repo_root/scripts/start-interactive-studio.sh"
  check_not_present '-p ' "$repo_root/scripts/start-interactive-studio.sh"
  check_not_present '--publish' "$repo_root/scripts/start-interactive-studio.sh"
  check_not_present 'auto-detect' "$repo_root/scripts/start-interactive-studio.sh"
  check_not_present 'sudo' "$repo_root/scripts/start-interactive-studio.sh"
  python3 - "$repo_root/scripts/start-interactive-studio.sh" <<'PY'
import pathlib, sys
path = pathlib.Path(sys.argv[1])
text = path.read_text()
run_pos = text.index("  docker_args+=(\n    run\n")
mount_pos = text.index("  while IFS='|' read -r host_path container_path mode purpose; do")
image_pos = text.index('    "$image"')
launch_pos = text.index('    -lc "$launch_command"')
if not (run_pos < mount_pos < image_pos < launch_pos):
    raise SystemExit("docker_args must start with run, then mounts, then image, then the container command")
if text.count('docker_args+=(-v "$host_path:$container_path:$mode")') != 1:
    raise SystemExit("expected exactly one mount expansion loop")
PY

  check_present 'docker stop' "$repo_root/scripts/stop-interactive-studio.sh"
  check_present 'stopped and retained' "$repo_root/scripts/stop-interactive-studio.sh"
  check_not_present '--rm' "$repo_root/scripts/stop-interactive-studio.sh"
  check_not_present 'docker prune' "$repo_root/scripts/stop-interactive-studio.sh"
  check_not_present 'docker rm' "$repo_root/scripts/stop-interactive-studio.sh"

  check_present 'docker rm' "$repo_root/scripts/restart-interactive-studio.sh"
  check_present 'explicit restart will remove the stopped Interactive Studio container' "$repo_root/scripts/restart-interactive-studio.sh"
  check_present 'removing exact Interactive Studio container before recreation' "$repo_root/scripts/restart-interactive-studio.sh"
  check_present 'stop-interactive-studio.sh' "$repo_root/scripts/restart-interactive-studio.sh"
  check_present 'start-interactive-studio.sh' "$repo_root/scripts/restart-interactive-studio.sh"
  check_present 'interactive_studio_container_name' "$repo_root/scripts/restart-interactive-studio.sh"
  check_not_present 'docker restart' "$repo_root/scripts/restart-interactive-studio.sh"
  check_not_present 'docker rm -f' "$repo_root/scripts/restart-interactive-studio.sh"
  check_not_present 'docker system prune' "$repo_root/scripts/restart-interactive-studio.sh"
  check_not_present 'docker container prune' "$repo_root/scripts/restart-interactive-studio.sh"

  check_present 'container absent' "$repo_root/scripts/status-interactive-studio.sh"
  check_present 'container exists but is stopped' "$repo_root/scripts/status-interactive-studio.sh"
  check_present 'Isaac Sim process: unknown' "$repo_root/scripts/status-interactive-studio.sh"
  check_present 'Kit readiness: unknown' "$repo_root/scripts/status-interactive-studio.sh"
  check_present 'Streaming readiness: unknown' "$repo_root/scripts/status-interactive-studio.sh"
  check_present 'Client connection: not observable' "$repo_root/scripts/status-interactive-studio.sh"
  check_present 'interactive_studio_readiness_markers' "$repo_root/scripts/status-interactive-studio.sh"
  check_present 'candidate marker -- pending validation against the pinned container logs' "$repo_root/scripts/status-interactive-studio.sh"

  check_present 'docker logs' "$repo_root/scripts/logs-interactive-studio.sh"
  check_present 'docker exec -it --user 1234:1234' "$repo_root/scripts/shell-interactive-studio.sh"

  check_present 'Supported host architecture' "$repo_root/scripts/validate-interactive-studio.sh"
  check_present 'docker info' "$repo_root/scripts/validate-interactive-studio.sh"
  check_present 'Pinned Interactive Studio image is not present locally' "$repo_root/scripts/validate-interactive-studio.sh"
  check_present 'Invalid required environment variable' "$repo_root/scripts/validate-interactive-studio.sh"
  check_present 'INTERACTIVE_STUDIO_HOST_IP' "$repo_root/scripts/validate-interactive-studio.sh"
  check_present 'Interactive Studio reuses a Phase 6 path' "$repo_root/scripts/validate-interactive-studio.sh"
  check_present 'Interactive Studio mount boundary is invalid' "$repo_root/scripts/validate-interactive-studio.sh"
  check_present 'Interactive Studio ports are not available' "$repo_root/scripts/validate-interactive-studio.sh"
  check_present 'launch prerequisites validated without starting Isaac Sim' "$repo_root/scripts/validate-interactive-studio.sh"
  check_not_present 'docker pull' "$repo_root/scripts/validate-interactive-studio.sh"
  check_not_present 'sudo' "$repo_root/scripts/validate-interactive-studio.sh"
  check_not_present 'os._exit()' "$repo_root/scripts/validate-interactive-studio.sh"

  check_present 'CONFIRM_CHOWN=1' "$repo_root/scripts/prepare-interactive-studio-ownership.sh"
  check_present 'runtime owner: 1234:1234' "$repo_root/scripts/prepare-interactive-studio-ownership.sh"
  check_present 'workspace owner:' "$repo_root/scripts/prepare-interactive-studio-ownership.sh"
  check_present 'shared assets: read-only, untouched' "$repo_root/scripts/prepare-interactive-studio-ownership.sh"
  check_present 'chmod 2775' "$repo_root/scripts/prepare-interactive-studio-ownership.sh"
  check_not_present 'sudo' "$repo_root/scripts/prepare-interactive-studio-ownership.sh"
  check_not_present 'docker rm' "$repo_root/scripts/prepare-interactive-studio-ownership.sh"
  check_not_present 'rm -rf' "$repo_root/scripts/prepare-interactive-studio-ownership.sh"

  check_present 'Run the ownership validator as the approved host user 1000' "$repo_root/scripts/validate-interactive-studio-ownership.sh"
  check_present 'docker "${docker_args[@]}" >/dev/null' "$repo_root/scripts/validate-interactive-studio-ownership.sh"
  check_present '--pull=never' "$repo_root/scripts/validate-interactive-studio-ownership.sh"
  check_present '--rm' "$repo_root/scripts/validate-interactive-studio-ownership.sh"
  check_present '--group-add' "$repo_root/scripts/validate-interactive-studio-ownership.sh"
  check_present 'Pinned Interactive Studio image is not present locally' "$repo_root/scripts/validate-interactive-studio-ownership.sh"
  check_present 'Interactive Studio root mode mismatch' "$repo_root/scripts/validate-interactive-studio-ownership.sh"
  check_present 'root traversal validated:' "$repo_root/scripts/validate-interactive-studio-ownership.sh"
  check_present 'if [[ "$path" == "$root" ]]; then' "$repo_root/scripts/validate-interactive-studio-ownership.sh"
  check_present 'interactive_studio_probe_container' "$repo_root/scripts/validate-interactive-studio-ownership.sh"
  check_present 'interactive_studio_probe_read_only_container' "$repo_root/scripts/validate-interactive-studio-ownership.sh"
  check_present 'interactive_studio_probe_host_workspace' "$repo_root/scripts/validate-interactive-studio-ownership.sh"
  check_present 'Workspace path mode mismatch' "$repo_root/scripts/validate-interactive-studio-ownership.sh"
  check_present 'probe succeeded:' "$repo_root/scripts/validate-interactive-studio-ownership.sh"
  check_present 'touch "$probe" >/dev/null 2>&1' "$repo_root/scripts/validate-interactive-studio-ownership.sh"
  check_present 'Shared Assets unexpectedly writable' "$repo_root/scripts/validate-interactive-studio-ownership.sh"
  check_present 'Shared Assets probe cleanup failed' "$repo_root/scripts/validate-interactive-studio-ownership.sh"
  check_present 'PASS: Shared Assets are read-only' "$repo_root/scripts/validate-interactive-studio-ownership.sh"
  check_present '.interactive-studio-host-workspace-probe' "$repo_root/scripts/validate-interactive-studio-ownership.sh"
  check_present '.interactive-studio-container-probe' "$repo_root/scripts/validate-interactive-studio-ownership.sh"
  check_present '.interactive-studio-shared-assets-readonly-probe' "$repo_root/scripts/validate-interactive-studio-ownership.sh"
  check_not_present '.interactive-studio-host-probe' "$repo_root/scripts/validate-interactive-studio-ownership.sh"
  check_not_present 'Runtime path ownership mismatch: /mnt/nvme/isaac/interactive-studio' "$repo_root/scripts/validate-interactive-studio-ownership.sh"
  check_not_present 'root ownership mismatch' "$repo_root/scripts/validate-interactive-studio-ownership.sh"
  check_not_present '|| true' "$repo_root/scripts/validate-interactive-studio-ownership.sh"
  check_not_present 'sudo' "$repo_root/scripts/validate-interactive-studio-ownership.sh"
  check_not_present '--privileged' "$repo_root/scripts/validate-interactive-studio-ownership.sh"
  check_not_present '--network=host' "$repo_root/scripts/validate-interactive-studio-ownership.sh"
  check_not_present '--gpus' "$repo_root/scripts/validate-interactive-studio-ownership.sh"
  check_not_present 'docker system prune' "$repo_root/scripts/validate-interactive-studio-ownership.sh"
  check_not_present 'docker container prune' "$repo_root/scripts/validate-interactive-studio-ownership.sh"
  check_not_present 'docker rm -f' "$repo_root/scripts/validate-interactive-studio-ownership.sh"

  check_present '.env.*.local' "$repo_root/.gitignore"
  check_present '.next/' "$repo_root/.gitignore"
  check_present 'out/' "$repo_root/.gitignore"
  check_present '*.py[cod]' "$repo_root/.gitignore"
  check_present '.coverage' "$repo_root/.gitignore"
  check_present 'htmlcov/' "$repo_root/.gitignore"
  check_present '*.swo' "$repo_root/.gitignore"
  check_present '*~' "$repo_root/.gitignore"
  check_present '!.env.example' "$repo_root/.gitignore"
  check_present '!config/lab.env.example' "$repo_root/.gitignore"
  check_not_present '.env*' "$repo_root/.gitignore"
  check_not_present '.idea/' "$repo_root/.gitignore"
  check_not_present '.vscode/' "$repo_root/.gitignore"
  check_not_present 'chmod 777' "$repo_root/scripts/prepare-interactive-studio-ownership.sh"

  check_present 'Interactive Studio' "$repo_root/docs/phase7-interactive-studio.md"
  check_present '/mnt/nvme/isaac/interactive-studio' "$repo_root/docs/phase7-interactive-studio.md"
  check_present '49100/TCP' "$repo_root/docs/phase7-interactive-studio.md"
  check_present '47998/UDP' "$repo_root/docs/phase7-interactive-studio.md"
  check_present 'trusted LAN or VPN only' "$repo_root/docs/phase7-interactive-studio.md"
  check_present 'container retained after a clean stop' "$repo_root/docs/phase7-interactive-studio.md"
  check_present 'bind-mounted host paths' "$repo_root/docs/phase7-interactive-studio.md"
  check_present 'exec ./runheadless.sh' "$repo_root/docs/phase7-interactive-studio.md"
  check_present 'primaryStream/publicIp' "$repo_root/docs/phase7-interactive-studio.md"
  check_present 'sudo mkdir -p /mnt/nvme/isaac/interactive-studio' "$repo_root/docs/phase7-interactive-studio.md"
  check_present 'group `1000` with setgid' "$repo_root/docs/phase7-interactive-studio.md"
  check_present 'collaborative umask of `0002`' "$repo_root/docs/phase7-interactive-studio.md"
  check_present 'Shared Assets are read-only' "$repo_root/docs/phase7-interactive-studio.md"

  check_present 'Phase 7: Interactive Studio, complete' "$repo_root/README.md"
  check_present 'Phase 7 Interactive Studio is complete' "$repo_root/docs/status.md"
  check_present 'Phase 7 Interactive Studio complete' "$repo_root/docs/status.md"
  check_present 'reconnect persistence validated' "$repo_root/docs/roadmap.md"
  check_present 'Hub Workstation Cache downloaded as a persistent package but intentionally deferred' "$repo_root/docs/phase7-interactive-studio.md"
  check_present 'Status: complete' "$repo_root/docs/roadmap.md"
  check_present 'Phase 7 overall complete' "$repo_root/docs/roadmap.md"
  check_present 'Phase 7: Interactive Studio, persistent launch, WebRTC acceptance, lifecycle recreation, and reconnect verification. Complete.' "$repo_root/docs/milestones.md"
  check_present 'Interactive Studio' "$repo_root/docs/roadmap.md"
  check_present '/mnt/nvme/isaac/interactive-studio' "$repo_root/docs/storage.md"
  check_present '/mnt/nvme/isaac/assets' "$repo_root/docs/storage.md"
  check_present 'Interactive Studio is the Phase 7 development environment' "$repo_root/docs/roadmap.md"
  check_present 'Phase 7 uses `/mnt/nvme/isaac/interactive-studio/` as the dedicated interactive runtime tree' "$repo_root/docs/storage.md"
  check_present 'Phase 7 workspace artifacts such as the saved smoke-test USD layers remain bind-mounted working content and stay outside git' "$repo_root/docs/storage.md"
  check_present 'Phase 7 package downloads such as `interactive-studio/pkg/hub-2.2.0` are persistent runtime artifacts, not tracked source' "$repo_root/docs/storage.md"
  check_present 'The approved stop target retained the exact Interactive Studio container' "$repo_root/docs/phase7-interactive-studio.md"
  check_present 'Docker stop ultimately returned exit code `137`' "$repo_root/docs/phase7-interactive-studio.md"
  check_present 'The package remains installed but inactive' "$repo_root/docs/phase7-interactive-studio.md"
  check_present 'Final scene metadata:' "$repo_root/docs/phase7-interactive-studio.md"
  check_present 'Phase 7 overall complete' "$repo_root/docs/phase7-interactive-studio.md"
  check_present 'Windows WebRTC connection succeeded' "$repo_root/docs/phase7-interactive-studio.md"
  check_present 'interactive authoring succeeded' "$repo_root/docs/phase7-interactive-studio.md"
  check_present 'lifecycle recreation complete' "$repo_root/docs/roadmap.md"
  check_present 'Windows reconnect and scene reopen complete' "$repo_root/docs/roadmap.md"
  check_present 'Docker stop ultimately returned exit code 137' "$repo_root/docs/status.md"
  check_present 'The next milestone is Phase 8: sensor foundations and device bring-up.' "$repo_root/README.md"

  for target in \
    prepare-interactive-studio \
    prepare-interactive-studio-ownership \
    validate-interactive-studio-ownership \
    start-interactive-studio \
    stop-interactive-studio \
    restart-interactive-studio \
    status-interactive-studio \
    logs-interactive-studio \
    shell-interactive-studio \
    validate-interactive-studio \
    test-phase7
  do
    check_make_target "$target"
  done

  check_not_present 'tooling.txt' "$repo_root/scripts/lib/interactive-studio.sh"
  check_not_present 'tooling.txt' "$repo_root/scripts/start-interactive-studio.sh"
  check_not_present 'tooling.txt' "$repo_root/scripts/stop-interactive-studio.sh"
  check_not_present 'tooling.txt' "$repo_root/scripts/validate-interactive-studio.sh"
  check_not_present 'tooling.txt' "$repo_root/scripts/restart-interactive-studio.sh"

  printf 'PASS: Phase 7 scaffold validated\n'
}

main "$@"
