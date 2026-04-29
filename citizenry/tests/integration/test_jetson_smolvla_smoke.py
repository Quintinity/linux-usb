"""Gated integration test — runs only on Jetson with CUDA + lerobot installed.

Skipped automatically when CUDA is unavailable or LEROBOT_INTEGRATION env
is unset.
"""

import os
import time

import numpy as np
import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("LEROBOT_INTEGRATION") != "1",
    reason="set LEROBOT_INTEGRATION=1 to run on Jetson",
)


def test_smolvla_loads_and_runs_under_target_latency():
    import torch
    if not torch.cuda.is_available():
        pytest.skip("no CUDA")
    from citizenry.smolvla_runner import SmolVLARunner
    r = SmolVLARunner(model_id="lerobot/smolvla_base", device="cuda")
    r.load()
    obs = {
        "observation.images.base": np.zeros((480, 640, 3), dtype=np.uint8),
        "observation.images.wrist": np.zeros((480, 640, 3), dtype=np.uint8),
        "observation.state": np.zeros(6, dtype=np.float32),
    }
    # Warm-up (first call always slow on CUDA)
    _ = r.act(obs)
    t0 = time.perf_counter()
    for _ in range(5):
        _ = r.act(obs)
    dt_ms = (time.perf_counter() - t0) * 1000.0 / 5.0
    print(f"[smolvla] avg inference {dt_ms:.1f}ms")
    assert dt_ms < 100.0, f"target <100ms; got {dt_ms:.1f}ms"
