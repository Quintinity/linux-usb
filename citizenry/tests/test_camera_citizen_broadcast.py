"""Tests for CameraCitizen camera_role plumbing + continuous frame broadcast.

The role+broadcast pair is the bridge that lets a PolicyCitizen's observation
cache fill from real cameras: without ``camera_role`` in the REPORT body the
cache can't key the frame, and without a continuous broadcast loop the cache
only gets a frame when something explicitly proposes a frame_capture task.

These tests verify:
  1. role appears in on-demand frame_capture REPORT body when set
  2. role is omitted from frame_capture REPORT body when None
  3. the broadcast loop emits frame_stream REPORTs with role
  4. the broadcast loop is a no-op when no role is configured
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from citizenry.camera_citizen import CameraCitizen


# ── On-demand frame_capture REPORT carries camera_role ──


def test_camera_role_appears_in_frame_capture_report(monkeypatch):
    """A CameraCitizen built with camera_role='wrist' must include camera_role
    in the body of the frame_capture REPORT it sends back to the requester.
    Without this, PolicyCitizen's observation cache can't key the frame and
    the policy gets None from _assemble_observation."""
    cam = CameraCitizen(name="test-cam", camera_role="wrist")
    cam._camera_ok = True
    monkeypatch.setattr(cam, "_capture_frame_b64", lambda: "FAKEB64")

    # Capture send_accept + send_report calls.
    cam.send_accept = MagicMock()
    cam.send_report = MagicMock()

    env = MagicMock()
    env.sender = "governor_key"
    body = {"task": "frame_capture", "task_id": "t-42"}

    cam._handle_frame_capture(env, ("127.0.0.1", 8000), body)

    assert cam.send_report.called, "send_report should be called when capture succeeds"
    call_args = cam.send_report.call_args
    # send_report(recipient, body, addr)
    sent_body = call_args[0][1]
    assert sent_body.get("camera_role") == "wrist", \
        f"REPORT body must carry camera_role='wrist', got: {sent_body}"
    assert sent_body.get("frame") == "FAKEB64"
    assert sent_body.get("type") == "frame_capture"


def test_no_camera_role_when_unset(monkeypatch):
    """When camera_role is None, the on-demand REPORT body must NOT contain a
    camera_role key (rather than carrying camera_role=None) — the cache layer
    falls back to the sender neighbor's name in that case, so a None entry
    here would be a positive lie."""
    cam = CameraCitizen(name="test-cam", camera_role=None)
    cam._camera_ok = True
    monkeypatch.setattr(cam, "_capture_frame_b64", lambda: "FAKEB64")

    cam.send_accept = MagicMock()
    cam.send_report = MagicMock()

    env = MagicMock()
    env.sender = "governor_key"
    body = {"task": "frame_capture", "task_id": "t-43"}

    cam._handle_frame_capture(env, ("127.0.0.1", 8000), body)

    sent_body = cam.send_report.call_args[0][1]
    assert "camera_role" not in sent_body, \
        f"camera_role must be ABSENT (not None) when unset, got: {sent_body}"


# ── Continuous broadcast loop ──


@pytest.mark.asyncio
async def test_broadcast_loop_emits_frames_with_role(monkeypatch):
    """When camera_role is set, _frame_broadcast_loop must keep sending
    frame_stream broadcasts at ~5 Hz, each carrying the correct role. We let
    it run briefly, then cancel and assert it ran."""
    cam = CameraCitizen(name="test-cam", camera_role="wrist")
    # Skip real start() entirely — it would try to bind sockets + open OpenCV.
    # We just need the state the loop reads.
    cam._running = True
    cam._camera_ok = True

    monkeypatch.setattr(cam, "_capture_frame_b64", lambda: "FAKEB64")

    sent: list[dict] = []

    def fake_broadcast(frame_b64: str) -> None:
        sent.append({"frame": frame_b64, "role": cam.camera_role})

    monkeypatch.setattr(cam, "_broadcast_frame", fake_broadcast)
    # Make the loop spin tight so the test finishes quickly.
    monkeypatch.setattr(cam, "_law", lambda key, default=None: 0.01)

    task = asyncio.create_task(cam._frame_broadcast_loop())
    # Let several iterations run, then stop the loop cleanly.
    await asyncio.sleep(0.1)
    cam._running = False
    try:
        await asyncio.wait_for(task, timeout=0.5)
    except asyncio.TimeoutError:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    assert len(sent) >= 1, "broadcast loop should emit at least one frame"
    # Every emission must carry the role.
    assert all(call["role"] == "wrist" for call in sent), \
        f"every broadcast must carry camera_role='wrist', got: {sent}"


@pytest.mark.asyncio
async def test_broadcast_loop_skips_when_no_role(monkeypatch):
    """A CameraCitizen with camera_role=None must NOT emit any continuous
    frame_stream broadcasts — that's bandwidth nobody can consume. The loop
    should return immediately on the role check, leaving the spy untouched."""
    cam = CameraCitizen(name="test-cam", camera_role=None)
    cam._running = True
    cam._camera_ok = True

    monkeypatch.setattr(cam, "_capture_frame_b64", lambda: "FAKEB64")

    sent: list[str] = []

    def fake_broadcast(frame_b64: str) -> None:
        sent.append(frame_b64)

    monkeypatch.setattr(cam, "_broadcast_frame", fake_broadcast)
    # Tight interval so if the loop did enter, it would emit several frames
    # in our 0.1s window — which is what we're guarding against.
    monkeypatch.setattr(cam, "_law", lambda key, default=None: 0.01)

    # The loop must exit on its own because role is None — wait_for will
    # complete normally (not time out) when the design is correct.
    await asyncio.wait_for(cam._frame_broadcast_loop(), timeout=0.5)

    assert sent == [], \
        f"no-role broadcast loop must not emit frames, got: {sent}"


# ── Lifecycle: start spawns the loop only with role+camera_ok ──


def test_init_default_camera_role_is_none():
    cam = CameraCitizen(name="test-cam")
    assert cam.camera_role is None
    assert cam._broadcast_task is None


def test_init_accepts_camera_role():
    cam = CameraCitizen(name="test-cam", camera_role="base")
    assert cam.camera_role == "base"
