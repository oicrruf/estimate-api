"""AT-266 three-domain service seam using repository-reviewed synthetic packs."""

import copy
import json
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pytest

from estimate_api.discovery.engine import revalidate
from estimate_api.discovery.models import KnowledgePackage, Need, ProjectIntake
from estimate_api.discovery.registry_adapter import RegistryContext
from estimate_api.discovery.service import evaluate_scope
from estimate_api.discovery.trusted import reviewed_package

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads(
    (ROOT / "src/estimate_api/discovery/data/reviewed-packages.v1.json").read_text()
)
CASES = {
    "cameras": (
        "catalog:camera-at266-v1",
        "camera:camera",
        8,
        10,
        "each",
        {"camera:link": 8, "camera:termination": 16, "camera:conduit": 40, "camera:mount": 8},
    ),
    "painting": (
        "catalog:painting-at266-v1",
        "painting:area",
        60,
        80,
        "m2",
        {"painting:coat": 120, "painting:paint": 12, "painting:masking": 2},
    ),
    "event": (
        "catalog:event-at266-v1",
        "event:speaker",
        4,
        6,
        "each",
        {
            "event:cable": 4,
            "event:stand": 4,
            "event:mixer": 1,
            "event:technician": 2,
            "event:power-load": 400,
        },
    ),
}


def setup(name: str) -> tuple[ProjectIntake, KnowledgePackage, RegistryContext]:
    package_id, root, quantity, _, unit, _ = CASES[name]
    item = next(p for p in MANIFEST["packages"] if p["id"] == package_id)
    project_name = "cameras" if name == "cameras" else name
    project = json.loads((ROOT / f"fixtures/valid/{project_name}.json").read_text())
    registry = json.loads((ROOT / "fixtures/knowledge/registry-synthetic.json").read_text())
    catalog = registry["packages"][0]
    catalog["id"] = package_id
    catalog["namespace"] = f"example.{name[:-1] if name == 'cameras' else name}"
    catalog["version"] = item["version"]
    catalog["source"]["ref"] = item["source"]
    catalog["source"]["version"] = item["version"]
    catalog["applicability"]["categories"] = [item["category"]]
    catalog["applicability"]["scopes"] = [item["scope"]]
    catalog["categorySpecs"][0]["category"] = item["category"]
    catalog["installationPatterns"] = [item["pattern"]]
    catalog["ruleSets"] = [
        {
            "id": "synthetic-reviewed-rules",
            "rules": [
                {"topic": r["id"], "choice": r["targetKey"], "sourceRef": r["sourceRef"]}
                for r in item["rules"]
            ],
        }
    ]
    intake = ProjectIntake(
        item["projectId"],
        item["domain"],
        item["jurisdiction"],
        "synthetic AT-266 example",
        (Need(root, quantity, unit),),
    )
    return (
        intake,
        reviewed_package(package_id),
        RegistryContext(project, registry, item["category"], item["scope"]),
    )


@pytest.mark.parametrize("name", CASES)
def test_actual_service_keeps_reviewed_lines_and_quantities(name: str) -> None:
    intake, package, context = setup(name)
    expected = CASES[name][5]
    before = evaluate_scope(intake, package, registry_context=context)
    lines = {line.key: line for line in before.proposal.lines}
    assert {key: lines[key].quantity for key in expected} == expected
    assert set(lines) == {CASES[name][1], *expected}
    assert all(lines[key].source_refs for key in expected)
    assert before.proposal.status == "pending_specialist"  # catalog is unverified
    assert not before.payload["commercialReady"]
    changed = replace(intake, needs=(Need(CASES[name][1], CASES[name][3], CASES[name][4]),))
    after = revalidate(before.proposal, changed, package)
    assert after.status == "pending_specialist"
    assert not after.commercial_ready
    assert {line.key for line in after.lines} == set(lines)
    assert all(line.state != "user_approved" for line in after.lines)
    changed_key, changed_quantity = {
        "cameras": ("camera:termination", 20),
        "painting": ("painting:paint", 16),
        "event": ("event:power-load", 600),
    }[name]
    assert (
        next(line.quantity for line in after.lines if line.key == changed_key) == changed_quantity
    )


@pytest.mark.parametrize(
    "name,foreign",
    [("cameras", "painting"), ("painting", "event"), ("event", "cameras")],
)
def test_undeclared_or_foreign_rule_is_rejected_by_both_entries(name: str, foreign: str) -> None:
    intake, package, context = setup(name)
    _, foreign_package, _ = setup(foreign)
    contaminated = replace(package, rules=package.rules + (foreign_package.rules[0],))
    scoped = evaluate_scope(intake, contaminated, registry_context=context)
    assert {line.key for line in scoped.proposal.lines} == {intake.needs[0].key}
    assert "reviewed_package_mismatch" in scoped.payload["coverage"]["reasons"]
    prior = evaluate_scope(intake, package, registry_context=context).proposal
    updated = revalidate(prior, intake, contaminated)
    assert {line.key for line in updated.lines} == {intake.needs[0].key}
    assert updated.status == "pending_specialist"
    assert not updated.commercial_ready


def test_catalog_declaration_and_source_revision_are_required() -> None:
    intake, package, context = setup("cameras")
    catalog = cast(dict[str, Any], copy.deepcopy(context.registry))
    catalog["packages"][0]["ruleSets"][0]["rules"][0]["sourceRef"] = "synthetic://changed"
    result = evaluate_scope(intake, package, registry_context=replace(context, registry=catalog))
    assert {line.key for line in result.proposal.lines} == {intake.needs[0].key}
    assert "reviewed_rule_declaration_missing" in result.payload["coverage"]["reasons"]
    changed_version = replace(package, version="2.0.0")
    result = evaluate_scope(intake, changed_version, registry_context=context)
    assert {line.key for line in result.proposal.lines} == {intake.needs[0].key}
    assert "reviewed_package_mismatch" in result.payload["coverage"]["reasons"]
    stale_catalog = cast(dict[str, Any], copy.deepcopy(context.registry))
    stale_catalog["packages"][0]["source"]["version"] = "draft-0"
    result = evaluate_scope(
        intake, package, registry_context=replace(context, registry=stale_catalog)
    )
    assert {line.key for line in result.proposal.lines} == {intake.needs[0].key}
    assert "reviewed_catalog_mismatch" in result.payload["coverage"]["reasons"]


def test_same_domain_rule_factor_cannot_be_silently_changed() -> None:
    intake, package, context = setup("painting")
    altered = replace(
        package,
        rules=(replace(package.rules[0], factor=99), *package.rules[1:]),
    )
    result = evaluate_scope(intake, altered, registry_context=context)
    assert {line.key for line in result.proposal.lines} == {"painting:area"}
    assert "reviewed_package_mismatch" in result.payload["coverage"]["reasons"]
    updated = revalidate(
        evaluate_scope(intake, package, registry_context=context).proposal, intake, altered
    )
    assert {line.key for line in updated.lines} == {"painting:area"}
    assert not updated.commercial_ready
