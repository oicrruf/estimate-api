"""Synthetic AT-267 checks in AT-240 proposal and revalidation."""

import copy
import json
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator

from estimate_api.contracts.universal_v1 import ProjectDocument
from estimate_api.discovery.constraint_adapter import assess_constraints, attach_constraints
from estimate_api.discovery.engine import discover, revalidate, review
from estimate_api.discovery.models import (
    KnowledgePackage,
    Need,
    ProjectIntake,
    ReviewAction,
    Rule,
)
from estimate_api.discovery.pattern_adapter import PatternBinding, build_pattern_plan
from estimate_api.discovery.service import (
    ScopeEvaluation,
    evaluate_pattern_scope,
    evaluate_scope,
    to_review_payload,
)
from estimate_api.patterns.v1 import Fact

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads((ROOT / "tests/at267/global_constraints.json").read_text())
CHECKS = (
    "global:total-ports",
    "global:poe-ports",
    "global:poe-power",
    "global:emt-model",
    "global:task-coverage",
    "global:permit-coverage",
)


def sufficient() -> dict[str, Any]:
    document = copy.deepcopy(FIXTURE)
    replacements = {
        "global:total-ports": ("limit", 9),
        "global:poe-power": ("limit", 120),
        "global:emt-model": ("allowed", ["emt-3-4"]),
        "global:task-coverage": ("provided", ["install", "test"]),
        "global:permit-coverage": ("provided", ["site-permit"]),
    }
    for package in document["packages"]:
        check = package["facts"]["check"]
        if check["id"] in replacements:
            field, value = replacements[check["id"]]
            check["inputs"][field]["value"] = value
    next(e for e in document["entities"] if e["id"] == "global:permit-provided")[
        "knowledgeState"
    ] = "known"
    return cast(dict[str, Any], document)


def inputs() -> tuple[ProjectIntake, KnowledgePackage]:
    intake = ProjectIntake(
        "global:goal", "synthetic", "TEST", "synthetic", (Need("camera", 8, "each"),)
    )
    package = KnowledgePackage(
        "synthetic",
        "1",
        "TEST",
        "synthetic://constraints-test",
        (
            Rule(
                "test:base",
                "camera",
                "mount",
                "material",
                "installation",
                "REQUIRES",
                "synthetic",
                quantity_mode="fixed",
                factor=1,
            ),
        ),
    )
    return intake, package


def evaluate(
    document: dict[str, Any] | None, required: tuple[str, ...] = CHECKS
) -> ScopeEvaluation:
    intake, package = inputs()
    return evaluate_scope(
        intake,
        package,
        constraint_document=cast(ProjectDocument, document) if document is not None else None,
        required_constraint_ids=required,
    )


def test_independent_port_poe_power_findings_and_review_gate() -> None:
    clean = evaluate(sufficient())
    assert clean.payload["constraints"] is not None
    assert {
        item["checkId"]: item["status"] for item in clean.payload["constraints"]["findings"]
    } == {key: "pass" for key in CHECKS}
    intake, package = inputs()
    clean_review = attach_constraints(
        discover(intake, package), assess_constraints(cast(ProjectDocument, sufficient()), CHECKS)
    )
    assert review(clean_review, (ReviewAction("mount", "approve"),)).status == "approved"
    for check_id, field, value in (
        ("global:total-ports", "limit", 8),
        ("global:poe-ports", "limit", 7),
        ("global:poe-power", "limit", 60),
    ):
        document = sufficient()
        check = next(
            p["facts"]["check"]
            for p in document["packages"]
            if p["facts"]["check"]["id"] == check_id
        )
        check["inputs"][field]["value"] = value
        scoped = evaluate(document)
        assert scoped.proposal.status != "approved"
        assert not scoped.payload["commercialReady"]
        assert f"constraint:{check_id}:fail" in scoped.proposal.technical_blockers
        gated = attach_constraints(
            discover(intake, package), assess_constraints(cast(ProjectDocument, document), CHECKS)
        )
        assert review(gated, (ReviewAction("mount", "approve"),)).status == "blocked"


def test_missing_stale_and_omitted_constraints_fail_closed() -> None:
    missing = evaluate(None)
    assert missing.proposal.status != "approved"
    assert missing.payload["constraints"] is not None
    assert missing.payload["constraints"]["missingCheckIds"] == list(CHECKS)
    document = sufficient()
    check = document["packages"][1]["facts"]["check"]
    check["inputs"]["limit"]["source"]["revision"] = 99
    stale = evaluate(document)
    assert "constraint:global:poe-ports:pending" in stale.proposal.technical_blockers
    assert stale.payload["constraints"] is not None
    assert stale.payload["constraints"]["findings"][1]["sources"] == []
    document = sufficient()
    document["packages"] = [
        p for p in document["packages"] if p["facts"]["check"]["id"] != "global:poe-power"
    ]
    omitted = evaluate(document)
    assert omitted.proposal.status != "approved"
    assert omitted.payload["constraints"] is not None
    assert omitted.payload["constraints"]["missingCheckIds"] == ["global:poe-power"]
    schema = json.loads(
        (ROOT / "src/estimate_api/discovery/schemas/scope-review.v1.schema.json").read_text()
    )
    Draft202012Validator(schema).validate(json.loads(json.dumps(omitted.payload)))
    mismatched = sufficient()
    mismatched["projectId"] = "different:goal"
    other = evaluate(mismatched)
    assert other.payload["constraints"] is not None
    assert other.payload["constraints"]["reason"] == "project_mismatch"
    assert not other.payload["commercialReady"]


def test_rejected_required_line_stays_blocked_after_constraint_pass() -> None:
    intake, package = inputs()
    scoped = attach_constraints(
        discover(intake, package), assess_constraints(cast(ProjectDocument, sufficient()), CHECKS)
    )
    rejected = review(scoped, (ReviewAction("mount", "reject"),))
    assert rejected.status == "blocked"
    assert not to_review_payload(rejected)["commercialReady"]


def test_revalidation_preserves_required_checks_when_document_is_omitted() -> None:
    intake = ProjectIntake(
        "global:goal", "synthetic", "TEST", "synthetic", (Need("camera", 8, "each"),)
    )
    patterns = json.loads((ROOT / "fixtures/patterns/patterns.v1.json").read_text())["patterns"]
    pattern = next(item for item in patterns if item["id"].endswith("poe-camera"))
    facts = {
        "application": {"state": "confirmed", "value": True, "evidenceId": "EV-APP"},
        "wired_run": {"state": "confirmed", "value": True, "evidenceId": "EV-WIRED"},
        "mount_required": {"state": "confirmed", "value": False, "evidenceId": "EV-MOUNT"},
        "poe_source": {"state": "confirmed", "value": True, "evidenceId": "EV-POE"},
        "utp_ends": {"state": "confirmed", "value": 2, "evidenceId": "EV-ENDS"},
    }
    plan = build_pattern_plan(
        intake,
        (PatternBinding("camera", pattern, cast(dict[str, Fact], facts)),),
        registry_package_id="catalog:camera-v1",
        source=pattern["sourceRef"],
    )
    first = evaluate_pattern_scope(
        intake,
        plan,
        constraint_document=cast(ProjectDocument, sufficient()),
        required_constraint_ids=CHECKS,
    )
    fresh = evaluate_pattern_scope(intake, plan, previous=first.proposal)
    assert fresh.proposal.constraint_check_ids == CHECKS
    assert fresh.proposal.status != "approved"
    assert fresh.proposal.technical_blockers
    assert fresh.payload["constraints"] is not None
    assert fresh.payload["constraints"]["missingCheckIds"] == list(CHECKS)
    assert not fresh.payload["commercialReady"]


def test_standalone_revalidate_requires_fresh_constraint_evidence() -> None:
    intake, package = inputs()
    prior = attach_constraints(
        discover(intake, package),
        assess_constraints(cast(ProjectDocument, sufficient()), CHECKS),
    )
    updated = revalidate(prior, intake, package)
    assert updated.status == "pending_specialist"
    assert updated.constraint_check_ids == CHECKS
    assert "constraint:document_missing" in updated.technical_blockers
    assert not updated.commercial_ready
