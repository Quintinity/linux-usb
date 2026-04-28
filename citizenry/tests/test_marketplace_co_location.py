"""Tests for the co-location bonus and follower-targeting filter."""

import pytest

from citizenry.marketplace import (
    Bid, Task, TaskMarketplace, TaskStatus,
    compute_bid_score, select_winner,
)


def test_co_location_bonus_added_when_node_matches():
    base = compute_bid_score(skill_level=5, current_load=0.0, health=1.0)
    boosted = compute_bid_score(
        skill_level=5, current_load=0.0, health=1.0,
        co_location_bonus=0.15,
    )
    assert boosted == pytest.approx(base + 0.15)


def test_co_location_bonus_zero_by_default():
    a = compute_bid_score(skill_level=5, current_load=0.0, health=1.0)
    b = compute_bid_score(
        skill_level=5, current_load=0.0, health=1.0,
        co_location_bonus=0.0,
    )
    assert a == b


def test_select_winner_score_only_no_implicit_bonus():
    """select_winner is bonus-agnostic — it picks the highest pre-computed score.
    The +0.15 lives inside the score; this test confirms select_winner doesn't
    add anything itself."""
    bids = [
        Bid(citizen_pubkey="a"*64, task_id="t", score=0.55,
            node_pubkey="n1", target_follower_pubkey="f1"),
        Bid(citizen_pubkey="b"*64, task_id="t", score=0.60,  # higher base
            node_pubkey="n2", target_follower_pubkey="f1"),
    ]
    winner = select_winner(bids)
    assert winner.citizen_pubkey == "b"*64


def test_can_citizen_bid_filters_on_follower_pubkey():
    mp = TaskMarketplace()
    task = Task(
        type="pick_and_place",
        params={"follower_pubkey": "f1"},
        required_capabilities=["6dof_arm"],
    )
    # Bidder targeting the right follower passes
    eligible, reason = mp.can_citizen_bid(
        task, ["6dof_arm"], [], 0.1, 1.0,
        target_follower_pubkey="f1",
    )
    assert eligible, reason
    # Bidder targeting a different follower is filtered
    eligible, reason = mp.can_citizen_bid(
        task, ["6dof_arm"], [], 0.1, 1.0,
        target_follower_pubkey="OTHER",
    )
    assert not eligible
    assert "follower" in reason.lower()


def test_can_citizen_bid_passes_when_task_has_no_follower_filter():
    """If task.params.follower_pubkey is absent, any target_follower_pubkey is fine."""
    mp = TaskMarketplace()
    task = Task(
        type="pick_and_place",
        params={},  # no follower_pubkey constraint
        required_capabilities=["6dof_arm"],
    )
    eligible, reason = mp.can_citizen_bid(
        task, ["6dof_arm"], [], 0.1, 1.0,
        target_follower_pubkey="anything",
    )
    assert eligible, reason


def test_bid_carries_node_pubkey_and_target_follower():
    bid = Bid(
        citizen_pubkey="a"*64, task_id="t", score=0.5,
        node_pubkey="n"*64, target_follower_pubkey="f"*64,
    )
    assert bid.node_pubkey == "n"*64
    assert bid.target_follower_pubkey == "f"*64
    d = bid.to_dict()
    assert d["node_pubkey"] == "n"*64
    assert d["target_follower_pubkey"] == "f"*64


def test_bid_from_accept_body_pulls_new_fields():
    body = {
        "task_id": "t",
        "bid": {
            "score": 0.5, "skill_level": 3, "load": 0.2, "health": 1.0,
            "estimated_duration": 4.0,
            "node_pubkey": "n"*64,
            "target_follower_pubkey": "f"*64,
        },
    }
    bid = Bid.from_accept_body(body, sender_pubkey="a"*64)
    assert bid.node_pubkey == "n"*64
    assert bid.target_follower_pubkey == "f"*64
