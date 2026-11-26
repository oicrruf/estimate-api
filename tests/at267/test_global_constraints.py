"""Synthetic AT-267 checks across package and evidence seams."""

import copy
import json
from pathlib import Path
from typing import Any, cast

import pytest

from estimate_api.constraints import Finding, evaluate_global_constraints
from estimate_api.contracts.universal_v1 import ProjectDocument, validate_project_document

FIXTURE = json.loads(Path(__file__).with_name("global_constraints.json").read_text())
PAINTING = json.loads(
    (Path(__file__).resolve().parents[2] / "fixtures/valid/painting.json").read_text()
)


def _find(document: dict[str, Any]) -> dict[str, Finding]:
    return {
        finding.check_id: finding
        for finding in evaluate_global_constraints(cast(ProjectDocument, document))
    }


def _check(document: dict[str, Any], check_id: str) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        next(
            package["facts"]["check"]
            for package in document["packages"]
            if package["facts"].get("check", {}).get("id") == check_id
        ),
    )


def _sufficient_solution() -> dict[str, Any]:
    document = copy.deepcopy(FIXTURE)
    _check(document, "global:total-ports")["inputs"]["limit"]["value"] = 9
    _check(document, "global:poe-power")["inputs"]["limit"]["value"] = 120
    _check(document, "global:emt-model")["inputs"]["allowed"]["value"] = ["emt-3-4"]
    _check(document, "global:task-coverage")["inputs"]["provided"]["value"] = [
        "install",
        "test",
    ]
    next(entity for entity in document["entities"] if entity["id"] == "global:permit-provided")[
        "knowledgeState"
    ] = "known"
    _check(document, "global:permit-coverage")["inputs"]["provided"]["value"] = ["site-permit"]
    return cast(dict[str, Any], document)


def test_sufficient_uplink_poe_and_power_are_independent_passes() -> None:
    findings = _find(_sufficient_solution())
    assert set(findings) == {
        "global:total-ports",
        "global:poe-ports",
        "global:poe-power",
        "global:emt-model",
        "global:task-coverage",
        "global:permit-coverage",
    }
    assert all(finding.status == "pass" and not finding.blocking for finding in findings.values())


@pytest.mark.parametrize(
    ("check_id", "operand", "value"),
    [
        ("global:total-ports", "limit", 8),
        ("global:poe-ports", "limit", 7),
        ("global:poe-power", "limit", 60),
    ],
)
def test_each_independent_capacity_failure(check_id: str, operand: str, value: int) -> None:
    document = _sufficient_solution()
    _check(document, check_id)["inputs"][operand]["value"] = value
    findings = _find(document)
    assert findings[check_id].status == "fail" and findings[check_id].blocking
    assert all(finding.status == "pass" for key, finding in findings.items() if key != check_id)


def test_real_synthetic_project_entry_and_separate_capacity_controls() -> None:
    assert validate_project_document(FIXTURE).valid
    findings = _find(FIXTURE)
    assert findings["global:total-ports"].status == "fail"  # 8 cameras + uplink > 8 total
    assert findings["global:poe-ports"].status == "pass"  # 8 PoE devices fit 8 PoE ports
    assert findings["global:poe-power"].status == "fail"  # watts evaluated independently
    assert findings["global:emt-model"].status == "fail"
    assert findings["global:task-coverage"].status == "fail"
    assert findings["global:permit-coverage"].status == "pending"
    assert all(finding.blocking for finding in findings.values() if finding.status != "pass")
    assert all(finding.sources for finding in findings.values() if finding.status != "pending")


def test_stale_or_missing_evidence_never_passes() -> None:
    document = copy.deepcopy(FIXTURE)
    document["packages"][1]["facts"]["check"]["inputs"]["limit"]["source"]["revision"] = 2
    assert _find(document)["global:poe-ports"].status == "pending"
    document = copy.deepcopy(FIXTURE)
    evidence = next(entity for entity in document["entities"] if entity["id"] == "global:evidence")
    evidence["relations"] = [
        relation
        for relation in evidence["relations"]
        if relation["targetId"] != "global:switch-poe"
    ]
    assert _find(document)["global:poe-ports"].status == "pending"
    document = copy.deepcopy(FIXTURE)
    document["packages"][1]["facts"]["check"]["inputs"]["limit"]["source"]["evidenceIds"] = []
    assert _find(document)["global:poe-ports"].status == "pending"


def test_invalid_or_unknown_check_fails_closed() -> None:
    document = copy.deepcopy(FIXTURE)
    document["packages"][1]["facts"]["check"]["kind"] = "magic"
    finding = _find(document)["global:poe-ports"]
    assert finding.status == "pending" and finding.blocking


def test_generic_coverage_on_painting_project() -> None:
    document = copy.deepcopy(PAINTING)
    envelope = {
        "origin": {"kind": "user", "ref": "synthetic-painting-brief-v2"},
        "scope": {"kind": "project", "id": "painting:project"},
        "revision": 1,
        "knowledgeState": "known",
    }
    document["entities"].extend(
        [
            {
                "id": "painting:coverage-constraint",
                "kind": "Constraint",
                "label": "Cobertura de preparación y pintura",
                **envelope,
            },
            {
                "id": "painting:coverage-evidence",
                "kind": "Evidence",
                "label": "Plan sintético",
                "relations": [
                    {"predicate": "supports", "targetId": "painting:task"},
                    {"predicate": "supports", "targetId": "painting:paint"},
                ],
                **envelope,
            },
        ]
    )

    def claim(value: list[str], entity_id: str) -> dict[str, Any]:
        return {
            "value": value,
            "source": {
                "entityId": entity_id,
                "revision": 1,
                "evidenceIds": ["painting:coverage-evidence"],
            },
        }

    document["packages"].append(
        {
            "id": "painting:coverage-package",
            "namespace": "estimate.constraints",
            "version": "1.0.0",
            "subjectId": "painting:coverage-constraint",
            "facts": {
                "check": {
                    "id": "painting:coverage-check",
                    "kind": "coverage",
                    "inputs": {
                        "required": claim(["prepare", "paint"], "painting:task"),
                        "provided": claim(["prepare"], "painting:paint"),
                    },
                }
            },
        }
    )
    assert validate_project_document(document).valid
    assert _find(document)["painting:coverage-check"].status == "fail"
    _check(document, "painting:coverage-check")["inputs"]["provided"]["value"].append("paint")
    assert _find(document)["painting:coverage-check"].status == "pass"
