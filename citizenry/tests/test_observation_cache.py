"""Tests for ObservationCache — per-citizen frame + state cache for PolicyCitizen."""

import numpy as np

from citizenry.observation_cache import ObservationCache


def test_cache_stores_and_retrieves_frame_by_camera_role():
    cache = ObservationCache()
    frame = np.zeros((96, 128, 3), dtype=np.uint8)
    cache.update_frame(camera_role="wrist", frame=frame, timestamp=1.0)
    out = cache.latest_frame("wrist", max_age_s=5.0, now=2.0)
    assert out is not None
    assert out.shape == frame.shape


def test_stale_frame_returns_none():
    cache = ObservationCache()
    cache.update_frame(camera_role="wrist", frame=np.zeros((48, 64, 3), dtype=np.uint8), timestamp=0.0)
    out = cache.latest_frame("wrist", max_age_s=0.1, now=10.0)
    assert out is None


def test_missing_frame_returns_none():
    cache = ObservationCache()
    out = cache.latest_frame("never_seen", max_age_s=5.0, now=1.0)
    assert out is None


def test_cache_stores_state_per_follower_pubkey():
    cache = ObservationCache()
    cache.update_state(follower_pubkey="abc", state=np.array([1, 2, 3, 4, 5, 6]), timestamp=1.0)
    out = cache.latest_state("abc", max_age_s=5.0, now=2.0)
    assert out is not None
    assert list(out) == [1, 2, 3, 4, 5, 6]


def test_state_accepts_list_input():
    cache = ObservationCache()
    cache.update_state(follower_pubkey="abc", state=[10, 20, 30, 40, 50, 60], timestamp=1.0)
    out = cache.latest_state("abc", max_age_s=5.0, now=2.0)
    assert out is not None
    assert list(out) == [10, 20, 30, 40, 50, 60]
    assert isinstance(out, np.ndarray)


def test_stale_state_returns_none():
    cache = ObservationCache()
    cache.update_state(follower_pubkey="abc", state=np.array([1, 2, 3]), timestamp=0.0)
    out = cache.latest_state("abc", max_age_s=0.1, now=10.0)
    assert out is None


def test_missing_state_returns_none():
    cache = ObservationCache()
    out = cache.latest_state("never_seen", max_age_s=5.0, now=1.0)
    assert out is None


def test_multiple_camera_roles_independent():
    cache = ObservationCache()
    f1 = np.zeros((10, 10, 3), dtype=np.uint8)
    f2 = np.ones((20, 20, 3), dtype=np.uint8)
    cache.update_frame("wrist", f1, timestamp=1.0)
    cache.update_frame("base", f2, timestamp=1.0)
    a = cache.latest_frame("wrist", max_age_s=5.0, now=2.0)
    b = cache.latest_frame("base", max_age_s=5.0, now=2.0)
    assert a is not None and a.shape == (10, 10, 3)
    assert b is not None and b.shape == (20, 20, 3)


def test_update_replaces_previous_frame():
    cache = ObservationCache()
    f1 = np.zeros((10, 10, 3), dtype=np.uint8)
    f2 = np.ones((10, 10, 3), dtype=np.uint8)
    cache.update_frame("wrist", f1, timestamp=1.0)
    cache.update_frame("wrist", f2, timestamp=2.0)
    out = cache.latest_frame("wrist", max_age_s=5.0, now=3.0)
    assert out is not None
    assert out[0, 0, 0] == 1  # the second frame's value


# --- Base-class wire-up tests: _sniff_observation_body on REPORT/ADVERTISE ---


def _make_report_envelope(sender_pubkey: str, body: dict):
    """Fake an Envelope-like object with the only fields _sniff_observation_body reads."""
    class _Env:
        sender = sender_pubkey
        type = 5  # MessageType.REPORT
    e = _Env()
    return e


def test_sniff_extracts_joint_positions_list_from_report():
    """A manipulator REPORT body containing joint_positions=[...] populates the
    state cache keyed by env.sender."""
    from citizenry.citizen import Citizen
    # Avoid running through Citizen.__init__ (which spins up transport, mDNS,
    # node identity, etc.) — bind only the bits _sniff_observation_body needs.
    c = Citizen.__new__(Citizen)
    c.observations = ObservationCache()
    c.neighbors = {}

    env = _make_report_envelope("follower_pk_1234", {})
    body = {"type": "state_share", "joint_positions": [11, 22, 33, 44, 55, 66], "timestamp": 100.0}
    Citizen._sniff_observation_body(c, env, body)

    out = c.observations.latest_state("follower_pk_1234", max_age_s=5.0, now=101.0)
    assert out is not None
    assert list(out) == [11, 22, 33, 44, 55, 66]


def test_sniff_extracts_joint_positions_dict_from_report():
    """A REPORT body with joint_positions as a dict (pain-event shape) is also
    accepted — values become the state vector in canonical MOTOR_NAMES order."""
    from citizenry.citizen import Citizen
    c = Citizen.__new__(Citizen)
    c.observations = ObservationCache()
    c.neighbors = {}

    env = _make_report_envelope("follower_pk_x", {})
    body = {
        "type": "pain_event",
        "joint_positions": {"shoulder_pan": 100, "shoulder_lift": 200, "elbow_flex": 300,
                             "wrist_flex": 400, "wrist_roll": 500, "gripper": 600},
        "timestamp": 50.0,
    }
    Citizen._sniff_observation_body(c, env, body)
    out = c.observations.latest_state("follower_pk_x", max_age_s=5.0, now=51.0)
    assert out is not None
    # Order must match MOTOR_NAMES — not sorted, not insertion order.
    assert list(out) == [100, 200, 300, 400, 500, 600]


def test_sniff_reorders_joint_positions_dict_to_motor_names_order():
    """Even when the dict is constructed in reverse insertion order, the state
    vector must come back in canonical MOTOR_NAMES order. This is the
    defensive-ordering contract that protects against senders that don't build
    dicts in MOTOR_NAMES order (e.g. PainEvent dicts, future state_share
    REPORTs)."""
    from citizenry.citizen import Citizen
    c = Citizen.__new__(Citizen)
    c.observations = ObservationCache()
    c.neighbors = {}

    env = _make_report_envelope("follower_pk_rev", {})
    # Reverse insertion order — gripper first, shoulder_pan last.
    body = {
        "type": "pain_event",
        "joint_positions": {
            "gripper":       600,
            "wrist_roll":    500,
            "wrist_flex":    400,
            "elbow_flex":    300,
            "shoulder_lift": 200,
            "shoulder_pan":  100,
        },
        "timestamp": 50.0,
    }
    Citizen._sniff_observation_body(c, env, body)
    out = c.observations.latest_state("follower_pk_rev", max_age_s=5.0, now=51.0)
    assert out is not None
    # Even with reversed dict, output is MOTOR_NAMES order.
    assert list(out) == [100, 200, 300, 400, 500, 600]


def test_sniff_extracts_position_from_telemetry_motors():
    """A telemetry REPORT body has per-motor positions under body['motors'] —
    sniff aggregates them into the state cache."""
    from citizenry.citizen import Citizen
    c = Citizen.__new__(Citizen)
    c.observations = ObservationCache()
    c.neighbors = {}

    env = _make_report_envelope("follower_pk_telem", {})
    body = {
        "type": "telemetry",
        "timestamp": 7.0,
        "motors": {
            "shoulder_pan":  {"position": 1000, "voltage": 7.4},
            "shoulder_lift": {"position": 2000, "voltage": 7.4},
            "elbow_flex":    {"position": 3000, "voltage": 7.4},
            "wrist_flex":    {"position": 4000, "voltage": 7.4},
            "wrist_roll":    {"position": 5000, "voltage": 7.4},
            "gripper":       {"position": 6000, "voltage": 7.4},
        },
    }
    Citizen._sniff_observation_body(c, env, body)
    out = c.observations.latest_state("follower_pk_telem", max_age_s=5.0, now=8.0)
    assert out is not None
    assert sorted(list(out)) == [1000, 2000, 3000, 4000, 5000, 6000]


def test_sniff_caches_frame_when_camera_role_present():
    """An ADVERTISE/REPORT body with frame=<b64-jpeg> + camera_role caches it."""
    from citizenry.citizen import Citizen
    import cv2
    import base64

    c = Citizen.__new__(Citizen)
    c.observations = ObservationCache()
    c.neighbors = {}

    # Encode a small JPEG so the decoder produces a real frame.
    img = (np.ones((32, 48, 3), dtype=np.uint8) * 50)
    ok, buf = cv2.imencode(".jpg", img)
    assert ok
    frame_b64 = base64.b64encode(buf.tobytes()).decode("ascii")

    env = _make_report_envelope("camera_pk_abc", {})
    body = {"type": "frame_capture", "frame": frame_b64, "camera_role": "wrist", "timestamp": 1.0}
    Citizen._sniff_observation_body(c, env, body)
    out = c.observations.latest_frame("wrist", max_age_s=5.0, now=2.0)
    assert out is not None
    assert out.shape == (32, 48, 3)


def test_sniff_falls_back_to_neighbor_name_for_camera_role():
    """When body lacks camera_role, fall back to the sender neighbor's name —
    cameras typically register as e.g. 'wrist' or 'wrist-cam'."""
    from citizenry.citizen import Citizen, Neighbor
    import cv2
    import base64

    c = Citizen.__new__(Citizen)
    c.observations = ObservationCache()
    c.neighbors = {
        "camera_pk_xyz": Neighbor(
            pubkey="camera_pk_xyz", name="wrist", citizen_type="camera",
            capabilities=["frame_capture"], addr=("127.0.0.1", 0),
        )
    }

    img = np.ones((16, 24, 3), dtype=np.uint8) * 99
    ok, buf = cv2.imencode(".jpg", img)
    assert ok
    frame_b64 = base64.b64encode(buf.tobytes()).decode("ascii")

    env = _make_report_envelope("camera_pk_xyz", {})
    body = {"type": "frame_capture", "frame": frame_b64, "timestamp": 1.0}  # no camera_role
    Citizen._sniff_observation_body(c, env, body)
    out = c.observations.latest_frame("wrist", max_age_s=5.0, now=2.0)
    assert out is not None
    assert out.shape == (16, 24, 3)


def test_sniff_ignores_non_dict_body():
    """A body that isn't a dict is silently ignored (no crash, no cache write)."""
    from citizenry.citizen import Citizen
    c = Citizen.__new__(Citizen)
    c.observations = ObservationCache()
    c.neighbors = {}
    env = _make_report_envelope("any", {})
    Citizen._sniff_observation_body(c, env, "not a dict")  # type: ignore[arg-type]
    Citizen._sniff_observation_body(c, env, None)  # type: ignore[arg-type]
    # No state was cached
    assert c.observations.latest_state("any", max_age_s=99.0, now=0.0) is None


def test_sniff_ignores_undecodable_jpeg():
    """A garbage 'frame' string doesn't blow up — it simply doesn't cache."""
    from citizenry.citizen import Citizen, Neighbor
    c = Citizen.__new__(Citizen)
    c.observations = ObservationCache()
    c.neighbors = {
        "cam": Neighbor(pubkey="cam", name="wrist", citizen_type="camera",
                        capabilities=[], addr=("127.0.0.1", 0))
    }
    env = _make_report_envelope("cam", {})
    body = {"type": "frame_capture", "frame": "not-a-real-jpeg-base64", "timestamp": 1.0}
    Citizen._sniff_observation_body(c, env, body)
    assert c.observations.latest_frame("wrist", max_age_s=5.0, now=2.0) is None
