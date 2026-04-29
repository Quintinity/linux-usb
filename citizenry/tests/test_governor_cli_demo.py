"""Tests for the governor_cli demo command."""

import asyncio
from unittest.mock import MagicMock, patch
import pytest

from citizenry.governor_cli import run_demo  # the new function we're building


@pytest.mark.asyncio
async def test_run_demo_prints_inventory_and_emits_task(capsys):
    surface = MagicMock()
    surface.name = "surface-governor"
    surface.pubkey = "abcdef0123456789"
    surface.neighbors = {
        "pi_pk": MagicMock(name="pi-inference", citizen_type="manipulator", capabilities=["6dof_arm"]),
        "jetson_pk": MagicMock(name="jetson-policy", citizen_type="policy", capabilities=["policy.imitation"]),
    }
    # MagicMock's auto-generated `name` kwarg sets the mock's repr-name, NOT the .name
    # attribute. Set .name explicitly so the demo's print sees the human-readable string.
    surface.neighbors["pi_pk"].name = "pi-inference"
    surface.neighbors["jetson_pk"].name = "jetson-policy"
    fake_task = MagicMock(id="t1", status=MagicMock(value="completed"), assigned_to="jetson_pk", created_at=0.0, completed_at=2.0)
    surface.create_task.return_value = fake_task
    surface.marketplace.tasks = {"t1": fake_task}
    with patch("citizenry.governor_cli.create_task_and_wait") as wait_mock:
        async def _fake_wait(*args, **kwargs):
            return {"task_id": "t1", "winner_pubkey": "jetson_pk", "winner_role": "policy", "status": "completed", "duration_s": 2.0}
        wait_mock.side_effect = _fake_wait
        await run_demo(surface, task_type="basic_gesture/wave")
    out = capsys.readouterr().out
    assert "inventory" in out.lower() or "neighbors" in out.lower()
    assert "jetson-policy" in out
    assert "completed" in out


@pytest.mark.asyncio
async def test_run_demo_narrates_no_bidder_timeout(capsys):
    """When create_task_and_wait raises TimeoutError (no bidder), the demo
    must surface that as a narrated outcome rather than propagating the
    traceback. This is the expected path when no arm is attached and a
    manipulation task gets zero bids — surfaced during live-mesh acceptance
    on 2026-04-29."""
    surface = MagicMock()
    surface.name = "surface-governor"
    surface.pubkey = "abcdef0123456789"
    surface.neighbors = {
        "pi_pk": MagicMock(citizen_type="brain", capabilities=["compute", "hailo_inference"]),
    }
    surface.neighbors["pi_pk"].name = "pi-inference"
    with patch("citizenry.governor_cli.create_task_and_wait") as wait_mock:
        async def _raise_timeout(*args, **kwargs):
            raise asyncio.TimeoutError("task did not complete in 30.0s")
        wait_mock.side_effect = _raise_timeout
        await run_demo(surface, task_type="basic_gesture/wave")
    out = capsys.readouterr().out
    assert "no bidder" in out.lower()
    assert "30s" in out or "30 s" in out
