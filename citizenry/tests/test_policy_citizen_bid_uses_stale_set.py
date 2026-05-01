"""When PolicyCitizen builds a bid, compute_bid_score sees the citizen's
stale_node_pubkeys (Sub-1 Task 6) — so the marketplace fix from Task 5
takes effect on the live bid path."""
from unittest.mock import patch

from citizenry.marketplace import Task, TaskStatus


def _isolate(monkeypatch, tmp_path):
    citizenry_dir = tmp_path / ".citizenry"
    citizenry_dir.mkdir()
    from citizenry import identity as identity_module
    from citizenry import node_identity as node_module
    monkeypatch.setattr(identity_module, "IDENTITY_DIR", citizenry_dir)
    monkeypatch.setattr(node_module, "IDENTITY_DIR", citizenry_dir)


class _StubRunner:
    """Minimal stub that satisfies PolicyCitizen's runner protocol surface."""
    def __init__(self): pass


def test_policy_bid_passes_stale_set_to_compute_bid_score(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    from citizenry.policy_citizen import PolicyCitizen

    p = PolicyCitizen(runner=_StubRunner(), name="policy-test", capabilities=[])
    # Pretend Sub-1 Task 6's handler ran and put a stale entry in the set
    p.stale_node_pubkeys = {"ab" * 32}

    # Make this bidder "co-located" with the targeted follower whose node
    # was rotated — bidder.node_pubkey == stale entry.
    p.node_pubkey = "ab" * 32

    captured: dict = {}

    def fake_compute(*args, **kwargs):
        captured.update(kwargs)
        return 0.5

    task = Task(
        id="t1",
        type="imitation_run",
        params={"target_follower_pubkey": "cd" * 32},
        required_capabilities=[],
        required_skills=["imitation:smolvla_base"],
        status=TaskStatus.BIDDING,
    )

    # PolicyCitizen.__init__ already awards level-1 XP to the imitation skill,
    # which is enough to pass the skill_tree.has_skill gate.

    with patch("citizenry.policy_citizen.compute_bid_score", side_effect=fake_compute):
        # Drive the canonical bid path: PolicyCitizen.build_bid invokes
        # compute_bid_score with the new stale-aware kwargs.
        bid = p.build_bid(
            task,
            target_follower_pubkey="cd" * 32,
            target_follower_node_pubkey="ab" * 32,
        )

    assert bid is not None, "bid was not built"
    assert "stale_node_pubkeys" in captured, (
        "compute_bid_score not called with stale_node_pubkeys kwarg"
    )
    assert captured["stale_node_pubkeys"] == {"ab" * 32}
    assert captured["bidder_node_pubkey"] == "ab" * 32
