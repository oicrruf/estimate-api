"""AT-265 catalog boundary tests with entirely synthetic declarations."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from estimate_api.contracts.universal_v1 import Scope
from estimate_api.knowledge.registry_v1 import CoverageResult, resolve_coverage, validate_registry

ROOT = Path(__file__).resolve().parents[2]
SCOPE: Scope = {"kind": "project", "id": "camera:project"}


def load(path: str) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    return load("fixtures/valid/cameras.json"), load("fixtures/knowledge/registry-synthetic.json")


def resolve(project: object, registry: object, **overrides: str) -> CoverageResult:
    args = {"jurisdiction": "TEST-ZONE-A", "category": "fictional-camera"} | overrides
    return resolve_coverage(project, registry, scope=SCOPE, **args)


def test_fixture_and_unverified_fail_closed() -> None:
    project, registry = inputs()
    assert validate_registry(registry).valid
    result = resolve(project, registry)
    assert result.status == "pending_specialist"
    assert result.package_ids == ("catalog:camera-v1",)
    assert result.reasons == ("unverified_package",)
    assert not result.conflicts


def test_missing_and_wrong_jurisdiction_are_unsupported() -> None:
    project, registry = inputs()
    assert resolve(project, {"schemaVersion": "1.0.0", "packages": []}).status == "unsupported"
    assert resolve(project, registry, jurisdiction="TEST-ZONE-B").status == "unsupported"
    assert resolve(project, registry, category="fictional-paint").status == "unsupported"
    project["packages"] = []
    assert resolve(project, registry).status == "unsupported"


def test_version_mismatch_and_scope_gap_are_unsupported() -> None:
    project, registry = inputs()
    registry["packages"][0]["version"] = "2.0.0"
    assert resolve(project, registry).status == "unsupported"
    _, registry = inputs()
    registry["packages"][0]["applicability"]["scopes"] = [
        {"kind": "site", "id": "camera:other-site"}
    ]
    assert resolve(project, registry).status == "unsupported"


def test_verified_metadata_only_catalogs_coverage() -> None:
    project, registry = inputs()
    review = registry["packages"][0]["review"]
    review.update(
        state="verified", reviewerRef="synthetic://reviewer", evidenceRefs=["synthetic://review"]
    )
    result = resolve(project, registry)
    assert result.status == "cataloged"
    assert result.reasons == ()


def test_overlap_and_contradiction_are_deterministic() -> None:
    project, registry = inputs()
    second = copy.deepcopy(registry["packages"][0])
    second["id"] = "catalog:alternative"
    second["namespace"] = "example.alternative"
    second["ruleSets"][0]["rules"][0]["choice"] = "beta"
    registry["packages"].insert(0, second)
    project["packages"].append(
        {
            "id": "camera:alternative",
            "namespace": "example.alternative",
            "version": "1.0.0",
            "subjectId": "camera:goal",
            "facts": {},
        }
    )
    result = resolve(project, registry)
    assert result.status == "pending_specialist"
    assert result.package_ids == ("catalog:alternative", "catalog:camera-v1")
    assert result.reasons == (
        "unverified_package",
        "overlapping_packages",
        "contradictory_declarations",
    )
    assert result.conflicts[0].topic == "fictional-choice"
    assert result.conflicts[0].declarations == (
        ("catalog:alternative", "beta"),
        ("catalog:camera-v1", "alpha"),
    )
    registry["packages"].reverse()
    assert resolve(project, registry) == result


def test_invalid_registry_and_scope_fail_closed() -> None:
    project, registry = inputs()
    registry["packages"][0]["review"]["state"] = "verified"
    assert not validate_registry(registry).valid
    assert resolve(project, registry).status == "pending_specialist"
    _, registry = inputs()
    registry["packages"].append(copy.deepcopy(registry["packages"][0]))
    assert not validate_registry(registry).valid
    _, registry = inputs()
    assert resolve_coverage(
        project,
        registry,
        jurisdiction="TEST-ZONE-A",
        category="fictional-camera",
        scope={"kind": "site", "id": "camera:nonexistent"},
    ).reasons == ("invalid_request_scope",)
