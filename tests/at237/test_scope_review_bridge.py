"""The local synthetic intake entry stays pending through AT-240 review."""

import copy
import json
from pathlib import Path
from typing import Any, cast

import pytest
from jsonschema import Draft202012Validator

from estimate_api.chat.scope_review_bridge import (
    ConstraintSnapshot,
    NetworkIntake,
    preview_scope_review,
)
from estimate_api.contracts.universal_v1 import ProjectDocument
from estimate_api.domain.scope_capture import Certainty, Fact, ScopeIntake

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads(
    (ROOT / "src/estimate_api/discovery/schemas/scope-review.v1.schema.json").read_text()
)


def intake(cameras: Fact[int] | None, uplink: Fact[int] | None) -> NetworkIntake:
    return NetworkIntake(
        ScopeIntake("Fictional site: PoE cameras and one separate network uplink."),
        cameras,
        uplink,
    )


def fact(value: int, evidence: str = "synthetic://confirmed") -> Fact[int]:
    return Fact(value, Certainty.CONFIRMED, evidence)


def snapshot() -> ConstraintSnapshot:
    fixture = (ROOT / "tests/at267/global_constraints.json").read_text()
    document = cast(ProjectDocument, json.loads(fixture.replace("global:goal", "camera:goal")))
    return ConstraintSnapshot(document, 8, 1)


def test_eight_poe_and_separate_uplink_stay_in_review() -> None:
    result = preview_scope_review(intake(fact(8), fact(1)), snapshot=snapshot())
    payload = result.scope_review.payload
    Draft202012Validator(SCHEMA).validate(payload)
    assert (result.stage, result.review_required, result.persisted) == (
        "scope_review_pending",
        True,
        False,
    )
    assert result.scope_draft.blocking_questions
    assert payload["schemaVersion"] == "scope-review.v1"
    assert payload["commercialReady"] is False
    lines = {line["key"]: line for line in payload["lines"]}
    assert lines["camera:camera"]["quantity"] == 8
    assert lines["network:uplink"]["quantity"] == 1
    assert lines["camera:link"]["quantity"] == 8
    assert lines["camera:termination"]["quantity"] == 16
    assert lines["camera:link"]["evidenceStatus"] == "unknown"
    assert payload["evidencePaths"]
    assert payload["constraints"] is not None
    findings = {item["checkId"]: item for item in payload["constraints"]["findings"]}
    assert findings["global:total-ports"]["status"] == "fail"  # 8 cameras + 1 uplink > 8
    assert findings["global:poe-ports"]["status"] == "pass"  # 8 PoE devices fit 8


def test_missing_evidence_never_derives_an_inferred_count() -> None:
    result = preview_scope_review(intake(Fact(8, Certainty.INFERRED), None))
    payload = result.scope_review.payload
    assert payload["commercialReady"] is False
    assert payload["constraints"] is not None
    assert payload["constraints"]["reason"] == "document_missing"
    lines = {line["key"]: line for line in payload["lines"]}
    assert lines["camera:camera"]["quantity"] is None
    assert lines["network:uplink"]["quantity"] is None
    assert lines["camera:link"]["quantity"] is None
    assert result.intake_questions == (
        "Confirm the PoE camera count with evidence.",
        "Confirm the separate uplink port count with evidence.",
    )
    with pytest.raises(ValueError, match="explicit evidence"):
        fact(8, "")


def test_changed_count_invalidates_prior_review_and_constraint_snapshot() -> None:
    first = preview_scope_review(intake(fact(8), fact(1)), snapshot=snapshot())
    with pytest.raises(ValueError, match="exact synthetic"):
        preview_scope_review(intake(fact(10), fact(1)), snapshot=snapshot())
    with pytest.raises(ValueError, match="separate fresh"):
        preview_scope_review(
            intake(fact(8), fact(1)), snapshot=snapshot(), previous=first.scope_review.proposal
        )
    changed = preview_scope_review(
        intake(fact(10, "synthetic://changed"), fact(1)), previous=first.scope_review.proposal
    )
    payload = changed.scope_review.payload
    Draft202012Validator(SCHEMA).validate(payload)
    assert changed.review_required and not changed.persisted
    assert payload["revision"] == 2 and payload["commercialReady"] is False
    assert payload["constraints"] is not None
    assert payload["constraints"]["reason"] == "document_missing"
    assert {item["key"] for item in payload["changes"]} >= {
        "camera:camera",
        "camera:link",
        "camera:termination",
    }
    assert next(line for line in payload["lines"] if line["key"] == "camera:link")["quantity"] == 10


def test_same_need_but_stale_or_changed_snapshot_fails_closed() -> None:
    fixed = snapshot()
    stale = cast(dict[str, Any], copy.deepcopy(fixed.document))
    for package in stale["packages"]:
        if package["facts"]["check"]["id"] == "global:total-ports":
            package["facts"]["check"]["inputs"]["demand"]["value"] = 8
    with pytest.raises(ValueError, match="exact synthetic"):
        preview_scope_review(
            intake(fact(8), fact(1)),
            snapshot=ConstraintSnapshot(cast(ProjectDocument, stale), 8, 1),
        )
