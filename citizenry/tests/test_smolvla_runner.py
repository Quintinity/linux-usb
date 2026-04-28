"""Tests for SmolVLARunner — model load is mocked; tests focus on shape contracts."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from citizenry.smolvla_runner import SmolVLARunner


def _fake_observation():
    return {
        "observation.images.base": np.zeros((96, 128, 3), dtype=np.uint8),
        "observation.images.wrist": np.zeros((96, 128, 3), dtype=np.uint8),
        "observation.state": np.array([100, 200, 300, 400, 500, 600], dtype=np.int32),
    }


@patch("citizenry.smolvla_runner._load_smolvla_policy")
def test_act_returns_action_chunk_of_expected_shape(load_mock):
    fake_policy = MagicMock()
    fake_policy.select_action.return_value = np.zeros((50, 6), dtype=np.float32)
    load_mock.return_value = fake_policy
    r = SmolVLARunner(model_id="lerobot/smolvla_base")
    r.load()
    chunk = r.act(_fake_observation())
    assert chunk.shape == (50, 6)
    assert chunk.dtype == np.float32


@patch("citizenry.smolvla_runner._load_smolvla_policy")
def test_act_before_load_raises(load_mock):
    r = SmolVLARunner(model_id="lerobot/smolvla_base")
    with pytest.raises(RuntimeError, match="not loaded"):
        r.act(_fake_observation())
