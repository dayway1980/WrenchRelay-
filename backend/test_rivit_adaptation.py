from rivit_adaptation import Evidence, select_evidence, build_adaptation_context, evaluate_adaptation
import pytest


def record(org, asset, rid, verified=True, source="technician_confirmed"):
    return Evidence(org, asset, rid, "Proximity sensor replaced; fault returned", verified, source)


def test_isolation_and_verified_only():
    rows = [record("a", "P-1", "1"), record("b", "P-1", "2"),
            record("a", "P-2", "3"), record("a", "P-1", "4", False),
            record("a", "P-1", "1"), record("a", "P-1", "5", True, "inference")]
    assert [r.record_id for r in select_evidence("a", "P-1", rows)] == ["1"]


def test_context_does_not_train_or_authorize_writes():
    result = build_adaptation_context("a", "P-1", [record("a", "P-1", "1")])
    assert result["mode"] == "retrieval_only_no_weight_updates"
    assert result["evidence"][0]["record_id"] == "1"
    assert any("Never automatically" in rule for rule in result["rules"])


def test_evaluation_cannot_self_promote():
    result = evaluate_adaptation([True, False], [True, True])
    assert result["accuracy_delta"] == .5
    assert result["promotion_approved"] is False
    with pytest.raises(ValueError):
        evaluate_adaptation([], [])
