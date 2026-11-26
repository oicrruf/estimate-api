"""Prueba ejecutable AT-261 con APIs integradas y datos enteramente ficticios."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, cast

from estimate_api.constraints.evaluate import evaluate_global_constraints
from estimate_api.contracts.universal_v1 import ProjectDocument, Scope, validate_project_document
from estimate_api.knowledge.registry_v1 import resolve_coverage, validate_registry

ROOT = Path(__file__).resolve().parents[2]


def _load(path: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads((ROOT / path).read_text(encoding="utf-8")))


def _scope(document: dict[str, Any]) -> Scope:
    goal = next(entity for entity in document["entities"] if entity["id"] == document["projectId"])
    return cast(Scope, goal["scope"])


def _event_check(event: dict[str, Any]) -> dict[str, Any]:
    document = copy.deepcopy(event)
    envelope = {
        "origin": {"kind": "system", "ref": "synthetic://handoff/event-check"},
        "scope": {"kind": "project", "id": "event:project"},
        "revision": 1,
        "knowledgeState": "known",
    }
    document["entities"].extend(
        [
            {
                "id": "event:permit-check",
                "kind": "Constraint",
                "label": "Permiso declarado",
                **envelope,
            },
            {
                "id": "event:permit-evidence",
                "kind": "Evidence",
                "label": "Acta ficticia",
                "relations": [
                    {"predicate": "supports", "targetId": "event:venue"},
                    {"predicate": "supports", "targetId": "event:permit"},
                ],
                **envelope,
            },
        ]
    )

    def claim(entity_id: str) -> dict[str, Any]:
        return {
            "value": ["venue-permit"],
            "source": {
                "entityId": entity_id,
                "revision": 1,
                "evidenceIds": ["event:permit-evidence"],
            },
        }

    document["packages"].append(
        {
            "id": "event:permit-check-package",
            "namespace": "estimate.constraints",
            "version": "1.0.0",
            "subjectId": "event:permit-check",
            "facts": {
                "check": {
                    "id": "event:permit-coverage",
                    "kind": "coverage",
                    "inputs": {"required": claim("event:venue"), "provided": claim("event:permit")},
                }
            },
        }
    )
    return document


def _finding_status(document: dict[str, Any]) -> tuple[str, bool]:
    result = validate_project_document(document)
    if not result.valid or result.document is None:
        raise AssertionError(f"documento de evento inválido: {result.issues}")
    findings = evaluate_global_constraints(cast(ProjectDocument, result.document))
    if len(findings) != 1:
        raise AssertionError(f"se esperaba un check: {findings}")
    return findings[0].status, findings[0].blocking


def run_smoke() -> dict[str, object]:
    """Devuelve estados deterministas; no autentica proyectos ni valida especialistas."""
    registry = _load("fixtures/knowledge/handoff-synthetic.json")
    if not validate_registry(registry).valid:
        raise AssertionError("registro sintético inválido")
    outcomes: dict[str, object] = {}
    for name, category in (("painting", "fictional-painting"), ("event", "fictional-event")):
        project = _load(f"fixtures/valid/{name}.json")
        if not validate_project_document(project).valid:
            raise AssertionError(f"proyecto {name} inválido")
        scope = _scope(project)
        pending = resolve_coverage(
            project, registry, jurisdiction="TEST-ZONE-A", category=category, scope=scope
        )
        claimed = copy.deepcopy(registry)
        for package in claimed["packages"]:
            package["review"].update(
                {
                    "state": "verified",
                    "reviewerRef": "synthetic://declared-reviewer",
                    "evidenceRefs": ["synthetic://declared-review-record"],
                }
            )
        cataloged = resolve_coverage(
            project, claimed, jurisdiction="TEST-ZONE-A", category=category, scope=scope
        )
        unsupported = resolve_coverage(
            project, claimed, jurisdiction="TEST-ZONE-B", category=category, scope=scope
        )
        wrong_category = resolve_coverage(
            project, claimed, jurisdiction="TEST-ZONE-A", category="fictional-other", scope=scope
        )
        wrong_version_registry = copy.deepcopy(claimed)
        for package in wrong_version_registry["packages"]:
            package["version"] = "2.0.0"
        wrong_version = resolve_coverage(
            project,
            wrong_version_registry,
            jurisdiction="TEST-ZONE-A",
            category=category,
            scope=scope,
        )
        if (
            pending.status != "pending_specialist"
            or pending.reasons != ("unverified_package",)
            or cataloged.status != "cataloged"
            or unsupported.status != "unsupported"
            or wrong_category.status != "unsupported"
            or wrong_version.status != "unsupported"
            or len(cataloged.package_ids) != 1
        ):
            raise AssertionError(f"cobertura inesperada para {name}")
        outcomes[name] = {
            "unverified": pending.status,
            "declaredReview": cataloged.status,
            "wrongJurisdiction": unsupported.status,
            "wrongCategory": wrong_category.status,
            "wrongVersion": wrong_version.status,
            "packageId": cataloged.package_ids[0],
        }

    event = _load("fixtures/valid/event.json")
    event_check = _event_check(event)
    assumed = _finding_status(event_check)
    next(entity for entity in event_check["entities"] if entity["id"] == "event:permit")[
        "knowledgeState"
    ] = "known"
    evidenced = _finding_status(event_check)
    next(entity for entity in event_check["entities"] if entity["id"] == "event:permit-evidence")[
        "relations"
    ] = [{"predicate": "supports", "targetId": "event:venue"}]
    broken = _finding_status(event_check)
    if assumed != ("pending", True) or evidenced != ("pass", False) or broken != ("pending", True):
        raise AssertionError("la evidencia crítica no produjo estados esperados")
    outcomes["eventEvidence"] = {
        "assumed": assumed[0],
        "supported": evidenced[0],
        "broken": broken[0],
    }
    return outcomes


if __name__ == "__main__":
    print(json.dumps(run_smoke(), sort_keys=True, indent=2))
