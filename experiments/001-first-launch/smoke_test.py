#!/usr/bin/env python3

import subprocess
import traceback

from isaacsim import SimulationApp

FRAME_COUNT = 10


def sample_gpu_memory_mib():
    try:
        output = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=memory.used",
                "--format=csv,noheader,nounits",
            ],
            text=True,
        ).strip()
    except Exception as exc:  # pragma: no cover - diagnostics only
        print(f"SMOKE: gpu memory sample failed: {exc}", flush=True)
        return None

    if not output:
        return None

    try:
        return int(output.splitlines()[0].strip())
    except ValueError:
        print(f"SMOKE: unexpected gpu memory sample: {output}", flush=True)
        return None


def main() -> int:
    print("SMOKE: python runtime started", flush=True)
    app = None
    peak_gpu_memory = None
    exit_code = 0

    try:
        app = SimulationApp(
            {
                "headless": True,
                "create_new_stage": False,
            }
        )
        print("SMOKE: SimulationApp initialized", flush=True)

        import isaacsim.core.experimental.utils.stage as stage_utils

        print("SMOKE: stage API imported", flush=True)

        current_gpu_memory = sample_gpu_memory_mib()
        if current_gpu_memory is not None:
            peak_gpu_memory = current_gpu_memory
            print(f"SMOKE: gpu memory used after init: {current_gpu_memory} MiB", flush=True)

        stage = stage_utils.create_new_stage(template="empty")
        if stage is None:
            raise RuntimeError("empty stage creation failed")
        print("SMOKE: empty stage created", flush=True)

        for frame in range(1, FRAME_COUNT + 1):
            app.update()
            current_gpu_memory = sample_gpu_memory_mib()
            if current_gpu_memory is not None:
                peak_gpu_memory = (
                    current_gpu_memory
                    if peak_gpu_memory is None
                    else max(peak_gpu_memory, current_gpu_memory)
                )
                print(
                    f"SMOKE: frame {frame}/{FRAME_COUNT} gpu_memory={current_gpu_memory} MiB",
                    flush=True,
                )
            else:
                print(f"SMOKE: frame {frame}/{FRAME_COUNT}", flush=True)

        print("SMOKE: simulation loop complete", flush=True)
        if peak_gpu_memory is not None:
            print(f"SMOKE: peak gpu memory observed: {peak_gpu_memory} MiB", flush=True)
        print("SMOKE: requesting immediate shutdown", flush=True)
    except Exception as exc:
        exit_code = 1
        print(f"SMOKE: FAILED: {exc}", flush=True)
        traceback.print_exc()
    finally:
        if app is not None:
            try:
                app.close(skip_cleanup=True, exit_code=exit_code)
            except Exception:
                exit_code = 1
                traceback.print_exc()

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
