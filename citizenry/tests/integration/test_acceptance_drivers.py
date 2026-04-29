"""Unit tests for the non-interactive acceptance driver."""

import asyncio
from unittest.mock import MagicMock

import pytest

from citizenry.governor_cli import create_task_and_wait


@pytest.mark.asyncio
async def test_create_task_and_wait_returns_when_task_completes():
    surface = MagicMock()
    task = MagicMock()
    task.id = "task-1"
    task.status = MagicMock(value="completed")
    task.assigned_to = "winner_pk"
    task.created_at = 0.0
    task.completed_at = 1.0
    surface.create_task.return_value = task
    surface.marketplace.tasks = {"task-1": task}
    # Inject a fake neighbor entry so winner_role/node resolve
    fake_nbr = MagicMock()
    fake_nbr.citizen_type = "policy"
    fake_nbr.node_pubkey = "jetson_node_pk"
    surface.neighbors = {"winner_pk": fake_nbr}

    out = await create_task_and_wait(
        surface=surface, task_type="pick_and_place",
        params={"follower_pubkey": "f1"},
        bid_window_s=0.0, completion_timeout_s=2.0,
    )
    assert out["task_id"] == "task-1"
    assert out["winner_pubkey"] == "winner_pk"
    assert out["status"] == "completed"
    assert out["winner_role"] == "policy"
    assert out["winner_node"] == "jetson_node_pk"
    assert out["follower_pubkey"] == "f1"
    assert out["duration_s"] == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_create_task_and_wait_timeout():
    surface = MagicMock()
    task = MagicMock()
    task.id = "task-2"
    task.status = MagicMock(value="executing")  # never completes
    surface.create_task.return_value = task
    surface.marketplace.tasks = {"task-2": task}
    surface.neighbors = {}
    with pytest.raises(asyncio.TimeoutError):
        await create_task_and_wait(
            surface=surface, task_type="pick_and_place",
            params={}, bid_window_s=0.0, completion_timeout_s=0.3,
        )


@pytest.mark.asyncio
async def test_create_task_and_wait_failed_status_returns():
    surface = MagicMock()
    task = MagicMock()
    task.id = "task-3"
    task.status = MagicMock(value="failed")
    task.assigned_to = ""
    task.created_at = 0.0
    task.completed_at = 0.5
    surface.create_task.return_value = task
    surface.marketplace.tasks = {"task-3": task}
    surface.neighbors = {}
    out = await create_task_and_wait(
        surface=surface, task_type="pick_and_place",
        params={}, bid_window_s=0.0, completion_timeout_s=2.0,
    )
    assert out["status"] == "failed"
    assert out["winner_pubkey"] == ""
    assert out["winner_role"] == ""
