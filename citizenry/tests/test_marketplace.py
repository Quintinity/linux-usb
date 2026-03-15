"""Tests for the task marketplace."""

import pytest
from citizenry.marketplace import (
    Task, Bid, TaskStatus, TaskMarketplace,
    compute_bid_score, select_winner, DEFAULT_WEIGHTS,
)


class TestTask:
    def test_create_task(self):
        t = Task(type="pick_and_place", priority=0.8)
        assert t.type == "pick_and_place"
        assert t.priority == 0.8
        assert t.status == TaskStatus.PENDING
        assert len(t.id) == 12

    def test_to_propose_body(self):
        t = Task(type="pick_and_place", priority=0.7, required_capabilities=["6dof_arm"])
        body = t.to_propose_body()
        assert body["task"] == "pick_and_place"
        assert body["task_id"] == t.id
        assert body["priority"] == 0.7
        assert body["required_capabilities"] == ["6dof_arm"]

    def test_from_propose_body(self):
        body = {
            "task": "wave",
            "task_id": "abc123",
            "priority": 0.5,
            "required_capabilities": ["6dof_arm"],
            "required_skills": ["basic_gesture"],
            "params": {"style": "friendly"},
        }
        t = Task.from_propose_body(body)
        assert t.id == "abc123"
        assert t.type == "wave"
        assert t.required_skills == ["basic_gesture"]


class TestBidScoring:
    def test_perfect_bid(self):
        score = compute_bid_score(skill_level=10, current_load=0.0, health=1.0)
        assert score == pytest.approx(1.0)

    def test_zero_bid(self):
        score = compute_bid_score(skill_level=0, current_load=1.0, health=0.0)
        assert score == pytest.approx(0.0)

    def test_mid_range(self):
        score = compute_bid_score(skill_level=5, current_load=0.5, health=0.5)
        expected = 0.4 * 0.5 + 0.3 * 0.5 + 0.3 * 0.5
        assert score == pytest.approx(expected)

    def test_skill_capped_at_10(self):
        s1 = compute_bid_score(skill_level=10, current_load=0.0, health=1.0)
        s2 = compute_bid_score(skill_level=20, current_load=0.0, health=1.0)
        assert s1 == s2

    def test_custom_weights(self):
        w = {"capability": 1.0, "availability": 0.0, "health": 0.0}
        score = compute_bid_score(skill_level=5, current_load=1.0, health=0.0, weights=w)
        assert score == pytest.approx(0.5)


class TestSelectWinner:
    def test_no_bids(self):
        assert select_winner([]) is None

    def test_single_bid(self):
        bid = Bid(citizen_pubkey="aaa", task_id="t1", score=0.5)
        assert select_winner([bid]) is bid

    def test_highest_score_wins(self):
        b1 = Bid(citizen_pubkey="aaa", task_id="t1", score=0.3)
        b2 = Bid(citizen_pubkey="bbb", task_id="t1", score=0.9)
        assert select_winner([b1, b2]) is b2

    def test_deterministic_tiebreak(self):
        b1 = Bid(citizen_pubkey="aaa", task_id="t1", score=0.5)
        b2 = Bid(citizen_pubkey="bbb", task_id="t1", score=0.5)
        winner = select_winner([b1, b2])
        # Same result regardless of input order
        winner2 = select_winner([b2, b1])
        assert winner.citizen_pubkey == winner2.citizen_pubkey


class TestTaskMarketplace:
    def test_create_task(self):
        mp = TaskMarketplace()
        t = mp.create_task("pick_and_place", priority=0.8)
        assert t.status == TaskStatus.BIDDING
        assert t.id in mp.tasks

    def test_add_bid(self):
        mp = TaskMarketplace()
        t = mp.create_task("wave")
        bid = Bid(citizen_pubkey="aaa", task_id=t.id, score=0.7)
        assert mp.add_bid(bid) is True
        assert len(mp.bids[t.id]) == 1

    def test_reject_bid_wrong_task(self):
        mp = TaskMarketplace()
        bid = Bid(citizen_pubkey="aaa", task_id="nonexistent", score=0.7)
        assert mp.add_bid(bid) is False

    def test_close_auction_with_winner(self):
        mp = TaskMarketplace()
        t = mp.create_task("wave")
        mp.add_bid(Bid(citizen_pubkey="aaa", task_id=t.id, score=0.3))
        mp.add_bid(Bid(citizen_pubkey="bbb", task_id=t.id, score=0.9))
        winner = mp.close_auction(t.id)
        assert winner.citizen_pubkey == "bbb"
        assert t.status == TaskStatus.ASSIGNED
        assert t.assigned_to == "bbb"

    def test_close_auction_no_bids(self):
        mp = TaskMarketplace()
        t = mp.create_task("wave")
        winner = mp.close_auction(t.id)
        assert winner is None
        assert t.status == TaskStatus.PENDING
        assert t.broadcast_count == 1

    def test_task_lifecycle(self):
        mp = TaskMarketplace()
        t = mp.create_task("wave")
        mp.add_bid(Bid(citizen_pubkey="aaa", task_id=t.id, score=0.5))
        mp.close_auction(t.id)
        assert mp.start_execution(t.id)
        assert t.status == TaskStatus.EXECUTING
        assert mp.complete_task(t.id, {"success": True})
        assert t.status == TaskStatus.COMPLETED
        assert len(mp.completed_tasks) == 1

    def test_fail_and_reauction(self):
        mp = TaskMarketplace()
        t = mp.create_task("wave")
        mp.add_bid(Bid(citizen_pubkey="aaa", task_id=t.id, score=0.5))
        mp.close_auction(t.id)
        mp.start_execution(t.id)
        reauction = mp.fail_task(t.id, "citizen_died")
        assert reauction is not None
        assert t.status == TaskStatus.BIDDING
        assert t.broadcast_count == 0  # Only incremented on no-bid close

    def test_can_citizen_bid(self):
        mp = TaskMarketplace()
        t = mp.create_task("pick", required_capabilities=["6dof_arm"], required_skills=["basic_grasp"])

        ok, _ = mp.can_citizen_bid(t, ["6dof_arm"], ["basic_grasp"], 0.1, 0.9)
        assert ok

        ok, reason = mp.can_citizen_bid(t, ["video_stream"], ["basic_grasp"], 0.1, 0.9)
        assert not ok
        assert "missing capability" in reason

        ok, reason = mp.can_citizen_bid(t, ["6dof_arm"], [], 0.1, 0.9)
        assert not ok
        assert "missing skill" in reason

        ok, reason = mp.can_citizen_bid(t, ["6dof_arm"], ["basic_grasp"], 0.1, 0.1)
        assert not ok
        assert "health" in reason
