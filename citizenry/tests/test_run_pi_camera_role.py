"""Tests for run_pi._camera_role_for_path — path-stable camera role mapping.

The role-from-path mapping is what survives the workshop-bench hotplug
scenario: cameras get plugged and unplugged while iterating, and we need
the role assignment to stick to the device (not to whatever the live-citizen
count happens to suggest at the moment hotplug fires).

If we derived role from `len(citizens)` instead, the failure mode is:
  1. /dev/video0 spawns as "wrist" (idx 0), /dev/video1 as "base" (idx 1).
  2. User unplugs /dev/video0 — it's removed from the citizens dict.
  3. User replugs /dev/video0 — hotplug fires; idx = 1 (only video1 left);
     role would resolve to "base" again. Now BOTH cameras broadcast as "base".
  4. PolicyCitizen never sees a "wrist" frame; _assemble_observation returns
     None forever.
"""

from __future__ import annotations

from citizenry.run_pi import _camera_role_for_path


def test_camera_role_for_path_maps_video0_to_wrist():
    assert _camera_role_for_path("/dev/video0") == "wrist"


def test_camera_role_for_path_maps_video1_to_base():
    assert _camera_role_for_path("/dev/video1") == "base"


def test_camera_role_for_path_returns_none_for_unknown():
    """Anything past video1 (or non-standard paths) gets no role and so
    won't broadcast a continuous frame_stream. The camera is still usable
    for on-demand frame_capture proposals."""
    assert _camera_role_for_path("/dev/video2") is None
    assert _camera_role_for_path("/dev/video10") is None
    assert _camera_role_for_path("/dev/null") is None
    assert _camera_role_for_path("") is None


def test_camera_role_stable_across_remove_add():
    """The whole point of path-based mapping: a remove+add cycle of the same
    /dev/videoN must yield the same role both times. Verified at the helper
    level — the asyncio hotplug machinery layered on top is just bookkeeping."""
    # Initial enumeration: video0 → wrist, video1 → base.
    initial_video0_role = _camera_role_for_path("/dev/video0")
    initial_video1_role = _camera_role_for_path("/dev/video1")
    assert initial_video0_role == "wrist"
    assert initial_video1_role == "base"

    # Notional: user unplugs /dev/video0, hotplug processes the removal.
    # (At the helper level, removal is a no-op — there's no state to clear.)

    # User replugs /dev/video0. Re-resolve role:
    replugged_video0_role = _camera_role_for_path("/dev/video0")

    # Must be the same role as before, NOT "base" (which would happen if role
    # were derived from a live-citizen count of 1 = the leftover video1).
    assert replugged_video0_role == initial_video0_role == "wrist"
    # And video1's role is unchanged regardless.
    assert _camera_role_for_path("/dev/video1") == initial_video1_role == "base"
