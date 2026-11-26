"""El handoff usa exclusivamente contratos integrados y dos rubros no cámara."""

from demo.architecture.smoke import run_smoke


def test_universal_handoff_smoke() -> None:
    result = run_smoke()
    assert set(result) == {"painting", "event", "eventEvidence"}
    for domain in ("painting", "event"):
        coverage = result[domain]
        assert isinstance(coverage, dict)
        assert coverage["unverified"] == "pending_specialist"
        assert coverage["declaredReview"] == "cataloged"
        assert coverage["wrongJurisdiction"] == "unsupported"
        assert coverage["wrongCategory"] == "unsupported"
        assert coverage["wrongVersion"] == "unsupported"
    assert result["eventEvidence"] == {
        "assumed": "pending",
        "supported": "pass",
        "broken": "pending",
    }
