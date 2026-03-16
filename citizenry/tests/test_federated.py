"""Tests for federated learning foundations."""

import pytest
from citizenry.federated import ModelWeightEnvelope, WeightRegistry, WeightRequest


class TestModelWeightEnvelope:
    def test_create(self):
        e = ModelWeightEnvelope(model_type="grasp_policy", version=1)
        assert e.model_type == "grasp_policy"
        assert len(e.id) == 12

    def test_roundtrip(self):
        e = ModelWeightEnvelope(
            model_type="sort_policy",
            version=3,
            metrics={"accuracy": 0.95},
            episodes_trained=100,
        )
        d = e.to_dict()
        e2 = ModelWeightEnvelope.from_dict(d)
        assert e2.model_type == "sort_policy"
        assert e2.metrics["accuracy"] == 0.95
        assert e2.episodes_trained == 100

    def test_announce_body(self):
        e = ModelWeightEnvelope(model_type="grasp_policy")
        body = e.to_announce_body()
        assert body["type"] == "model_weights_available"
        assert body["envelope"]["model_type"] == "grasp_policy"


class TestWeightRequest:
    def test_to_propose_body(self):
        r = WeightRequest(requester_pubkey="aaa", envelope_id="env123")
        body = r.to_propose_body()
        assert body["task"] == "weight_transfer"
        assert body["envelope_id"] == "env123"


class TestWeightRegistry:
    def test_register(self):
        reg = WeightRegistry()
        e = ModelWeightEnvelope(model_type="grasp")
        reg.register(e)
        assert reg.count() == 1
        assert "grasp" in reg.list_types()

    def test_get_latest(self):
        reg = WeightRegistry()
        reg.register(ModelWeightEnvelope(model_type="grasp", version=1))
        reg.register(ModelWeightEnvelope(model_type="grasp", version=3))
        reg.register(ModelWeightEnvelope(model_type="grasp", version=2))
        latest = reg.get_latest("grasp")
        assert latest.version == 3

    def test_get_latest_missing(self):
        reg = WeightRegistry()
        assert reg.get_latest("nonexistent") is None

    def test_get_best(self):
        reg = WeightRegistry()
        reg.register(ModelWeightEnvelope(model_type="grasp", version=1, metrics={"accuracy": 0.8}))
        reg.register(ModelWeightEnvelope(model_type="grasp", version=2, metrics={"accuracy": 0.95}))
        best = reg.get_best("grasp", "accuracy")
        assert best.version == 2

    def test_get_best_no_metric(self):
        reg = WeightRegistry()
        reg.register(ModelWeightEnvelope(model_type="grasp", version=1))
        assert reg.get_best("grasp", "accuracy") is None

    def test_to_list(self):
        reg = WeightRegistry()
        reg.register(ModelWeightEnvelope(model_type="grasp"))
        reg.register(ModelWeightEnvelope(model_type="sort"))
        lst = reg.to_list()
        assert len(lst) == 2
