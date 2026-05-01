"""compute_bid_score honours the stale_node_pubkeys set populated by
GOVERN(rotate_node_key) — co-location bonus is suppressed for stale bidders."""
import pytest

from citizenry.marketplace import compute_bid_score


def test_bonus_applied_when_bidder_node_not_stale():
    """Baseline: with no stale set, co-location bonus is applied as before."""
    score = compute_bid_score(
        skill_level=8,
        current_load=0.2,
        health=1.0,
        co_location_bonus=0.15,
        bidder_node_pubkey="ab" * 32,
        stale_node_pubkeys=set(),
    )
    base = compute_bid_score(skill_level=8, current_load=0.2, health=1.0)
    assert score == pytest.approx(base + 0.15)


def test_bonus_suppressed_when_bidder_node_in_stale_set():
    """Smell #5 fix: stale node_pubkey → no co-location bonus."""
    score = compute_bid_score(
        skill_level=8,
        current_load=0.2,
        health=1.0,
        co_location_bonus=0.15,
        bidder_node_pubkey="ab" * 32,
        stale_node_pubkeys={"ab" * 32},
    )
    base = compute_bid_score(skill_level=8, current_load=0.2, health=1.0)
    assert score == pytest.approx(base)


def test_legacy_call_signature_still_works():
    """Pre-Sub-2 callers that pass neither bidder_node_pubkey nor
    stale_node_pubkeys must continue to receive the bonus."""
    score = compute_bid_score(
        skill_level=8, current_load=0.2, health=1.0,
        co_location_bonus=0.15,
    )
    base = compute_bid_score(skill_level=8, current_load=0.2, health=1.0)
    assert score == pytest.approx(base + 0.15)


def test_no_bonus_no_suppression_check():
    """If co_location_bonus is 0 the stale set is irrelevant."""
    score = compute_bid_score(
        skill_level=5, current_load=0.4, health=0.9,
        co_location_bonus=0.0,
        bidder_node_pubkey="cd" * 32,
        stale_node_pubkeys={"cd" * 32},
    )
    expected = compute_bid_score(skill_level=5, current_load=0.4, health=0.9)
    assert score == pytest.approx(expected)


def test_empty_bidder_node_pubkey_does_not_match_stale_set():
    """A bidder that did not declare its node pubkey cannot accidentally match
    a stale entry of the empty string. Defensive."""
    score = compute_bid_score(
        skill_level=8, current_load=0.2, health=1.0,
        co_location_bonus=0.15,
        bidder_node_pubkey="",
        stale_node_pubkeys={""},
    )
    base = compute_bid_score(skill_level=8, current_load=0.2, health=1.0)
    assert score == pytest.approx(base + 0.15)
