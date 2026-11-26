"""Named synthetic harness for the AT-240 orchestration boundary."""

import copy
import json
from dataclasses import replace
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from estimate_api.discovery import (
    KnowledgePackage,
    ProjectIntake,
    ReviewAction,
    discover,
    revalidate,
    review,
)
from estimate_api.discovery.hardware_adapter import evaluate_hardware_scope
from estimate_api.discovery.models import Need, Rule
from estimate_api.discovery.registry_adapter import RegistryContext
from estimate_api.discovery.service import SCHEMA_VERSION, evaluate_scope, to_review_payload

FIXTURE = Path(__file__).resolve().parents[1] / "demo/fixtures/at-240-discovery.json"
SCHEMA = (
    Path(__file__).resolve().parents[1]
    / "src/estimate_api/discovery/schemas/scope-review.v1.schema.json"
)
HARDWARE_FIXTURE = Path(__file__).resolve().parents[1] / "demo/hardware/fixture.json"
ROOT = Path(__file__).resolve().parents[1]


def registry_context() -> RegistryContext:
    project = json.loads((ROOT / "fixtures/valid/cameras.json").read_text(encoding="utf-8"))
    registry = json.loads(
        (ROOT / "fixtures/knowledge/registry-synthetic.json").read_text(encoding="utf-8")
    )
    return RegistryContext(
        project, registry, "fictional-camera", {"kind": "project", "id": "camera:project"}
    )


def sample() -> tuple[ProjectIntake, KnowledgePackage]:
    payload = json.loads(FIXTURE.read_text())
    project = payload["project"]
    package = payload["package"]
    return (
        ProjectIntake(**{**project, "needs": tuple(Need(**need) for need in project["needs"])}),
        KnowledgePackage(
            **{
                **package,
                "rules": tuple(
                    Rule(**{**rule, "evidence_ids": tuple(rule.get("evidence_ids", ()))})
                    for rule in package["rules"]
                ),
            }
        ),
    )


def test_discovery_exposes_requested_proposed_pending_and_evidence() -> None:
    intake, package = sample()
    proposal = discover(intake, package)
    lines = {line.key: line for line in proposal.lines}
    assert proposal.status == "proposed" and not proposal.commercial_ready
    assert lines["camera"].state == "user_requested"
    assert lines["ethernet_link"].quantity == 8
    assert lines["termination"].quantity == 16
    assert lines["mount"].state == "agent_proposed"
    assert lines["cable_length"].quantity is None
    assert lines["cable_length"].state == "pending_measurement"
    assert lines["pathway_length"].quantity is None
    assert all(line.source and line.package_version == "1.0.0" for line in proposal.lines[3:])
    assert ("ethernet_link", "TERMINATES_AT", "termination") in proposal.evidence_paths
    assert proposal.work_packages["links"] == "pending"
    assert len(proposal.questions) == 4


def test_approval_gate_rejection_and_measurement() -> None:
    intake, package = sample()
    proposal = discover(intake, package)
    blocked = review(proposal, (ReviewAction("termination", "reject"),))
    assert blocked.status == "blocked" and not blocked.commercial_ready
    assert blocked.work_packages["terminations"] == "incomplete"
    with pytest.raises(ValueError, match="Measure"):
        review(proposal, (ReviewAction("cable_length", "approve"),))
    actions = []
    for line in proposal.lines:
        if line.state == "pending_measurement":
            measured = review(proposal, (ReviewAction(line.key, "modify", 1, line.unit),))
            assert measured.lines != proposal.lines and not measured.commercial_ready
            actions.append(ReviewAction(line.key, "modify", 1, line.unit))
    measured = review(proposal, tuple(actions))
    final = review(
        measured,
        tuple(
            ReviewAction(line.key, "approve")
            for line in measured.lines
            if line.state == "agent_proposed"
        ),
    )
    assert final.status == "approved" and final.commercial_ready
    optional_rejected = review(final, (ReviewAction("cabinet", "reject"),))
    assert optional_rejected.status == "approved" and optional_rejected.commercial_ready


def test_revalidation_invalidates_approval_and_reports_quantity_impact() -> None:
    intake, package = sample()
    proposal = discover(intake, package)
    approved_one = review(proposal, (ReviewAction("termination", "approve"),))
    changed_needs = tuple(
        replace(need, quantity=12) if need.key == "camera" else need for need in intake.needs
    )
    changed = revalidate(approved_one, replace(intake, needs=changed_needs), package)
    lines = {line.key: line for line in changed.lines}
    assert lines["ethernet_link"].quantity == 12
    assert lines["termination"].quantity == 24
    assert lines["termination"].state == "agent_proposed"
    assert ("termination", "changed") in changed.changes
    assert not changed.commercial_ready
    no_emt = revalidate(changed, replace(intake, facts={"link_design": "wired"}), package)
    assert ("pathway_length", "removed") in no_emt.changes


def test_uncovered_specialty_and_second_domain() -> None:
    intake, _ = sample()
    pending = discover(intake, None)
    assert pending.status == "pending_specialist" and not pending.commercial_ready
    other = ProjectIntake(
        "SYN-OTHER", "synthetic_lighting", "SYN", "Light a room", (Need("luminaire", 2, "each"),)
    )
    pack = KnowledgePackage(
        "synthetic_lighting",
        "v1",
        "SYN",
        "fictitious rule",
        (
            Rule(
                "l1",
                "luminaire",
                "mounting_service",
                "service",
                "install",
                "REQUIRES",
                "synthetic evidence",
                quantity_mode="fixed",
                factor=1,
            ),
        ),
    )
    result = discover(other, pack)
    assert {line.key for line in result.lines} == {"luminaire", "mounting_service"}
    assert result.lines[1].source == "fictitious rule | synthetic evidence"
    assert discover(other, replace(pack, jurisdiction="OTHER")).status == "pending_specialist"
    assert discover(other, replace(pack, rules=())).status == "pending_specialist"


def test_bounded_rules_and_cycle_detection() -> None:
    intake, package = sample()
    with pytest.raises(ValueError, match="depth"):
        discover(intake, package, max_depth=1)
    with pytest.raises(ValueError, match="line limit"):
        discover(intake, package, max_lines=3)
    cycle = replace(
        package,
        rules=package.rules
        + (
            Rule(
                "cycle",
                "ethernet_link",
                "camera",
                "equipment",
                "links",
                "REQUIRES",
                "synthetic cycle",
            ),
        ),
    )
    with pytest.raises(ValueError, match="cycle"):
        discover(intake, cycle)


def test_unknown_topology_fact_blocks_commercial_readiness() -> None:
    intake, package = sample()
    undecided = discover(replace(intake, facts={}), package)
    assert undecided.status == "proposed"
    assert undecided.blocking_facts == ("link_design",)
    assert not undecided.commercial_ready
    assert any("link_design" in question for question in undecided.questions)
    approved = review(
        undecided,
        tuple(
            ReviewAction(line.key, "approve")
            for line in undecided.lines
            if line.state == "agent_proposed"
        ),
    )
    assert approved.status == "proposed" and not approved.commercial_ready


def test_versioned_review_payload_preserves_unknown_and_pending() -> None:
    intake, package = sample()
    evaluated = evaluate_scope(intake, package)
    payload = evaluated.payload
    assert payload["schemaVersion"] == SCHEMA_VERSION
    assert payload["projectId"] == intake.project_id
    assert payload["status"] == "pending_specialist"
    assert payload["coverage"]["reasons"] == ["registry_mapping_missing"]
    assert not payload["commercialReady"]
    lines = {line["key"]: line for line in payload["lines"]}
    assert lines["camera"]["actions"] == []
    assert lines["ethernet_link"]["evidenceStatus"] == "unknown"
    assert "approve" not in lines["cable_length"]["actions"]
    assert payload["changes"] == []
    assert to_review_payload(evaluated.proposal) == payload
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(json.loads(json.dumps(payload)))


def test_shared_dependency_requires_quantity_confirmation() -> None:
    intake, package = sample()
    shared = replace(
        package,
        rules=package.rules
        + (
            Rule(
                "shared",
                "mesh_node",
                "mount",
                "accessory",
                "mounting",
                "MOUNTED_ON",
                "illustrative shared resource",
                quantity_mode="same",
            ),
        ),
    )
    proposal = discover(intake, shared)
    assert ("mesh_node", "MOUNTED_ON", "mount") in proposal.evidence_paths
    assert "quantity:mount" in proposal.blocking_facts
    assert any("mount" in question for question in proposal.questions)
    assert not proposal.commercial_ready


def test_uncovered_required_need_cannot_disappear_from_proposal() -> None:
    intake, package = sample()
    added = replace(intake, needs=intake.needs + (Need("uncovered_need", None, "each"),))
    proposal = discover(added, package)
    assert proposal.status == "pending_specialist"
    assert "uncovered_need" in {line.key for line in proposal.lines if line.required}
    assert any("uncovered_need" in question for question in proposal.questions)
    assert not proposal.commercial_ready


def test_confirmed_hardware_route_and_unknown_do_not_invent_counts() -> None:
    fixture = json.loads(HARDWARE_FIXTURE.read_text(encoding="utf-8"))
    catalog, routes = fixture["catalog"], fixture["routes"]
    confirmed = evaluate_hardware_scope(catalog, routes["confirmed"])
    assert confirmed.status == "REVIEW_REQUIRED"
    assert {line.family: line.quantity for line in confirmed.lines} == {
        "emt": 2,
        "coupling": 1,
        "support": 3,
    }
    assert confirmed.missing[0].family == "connector"
    assert confirmed.missing[0].quantity == 2
    assert "GEN-CONNECTOR-1" in confirmed.missing[0].alternatives
    assert all(line.rule_id and line.evidence_ids for line in confirmed.lines)
    assert confirmed.professional_validation_required
    unknown = evaluate_hardware_scope(catalog, routes["unknown"])
    assert unknown.status == "PENDING"
    assert unknown.lines == () and unknown.missing == ()
    intake, package = sample()
    confirmed_payload = evaluate_scope(intake, package, hardware_scope=confirmed).payload
    unknown_payload = evaluate_scope(intake, package, hardware_scope=unknown).payload
    assert confirmed_payload["hardware"] is not None
    assert confirmed_payload["hardware"]["missing"][0]["quantity"] == 2
    assert unknown_payload["hardware"] is not None
    assert unknown_payload["hardware"]["lines"] == []
    assert unknown_payload["hardware"]["missing"] == []
    assert not confirmed_payload["commercialReady"]
    assert not unknown_payload["commercialReady"]
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    for payload in (confirmed_payload, unknown_payload):
        Draft202012Validator(schema).validate(json.loads(json.dumps(payload)))


def test_registry_coverage_fails_closed_and_matches_pattern_identity() -> None:
    intake, package = sample()
    context = registry_context()
    pending = evaluate_scope(intake, package, registry_context=context)
    assert pending.proposal.status == "pending_specialist"
    assert pending.payload["coverage"]["reasons"] == ["unverified_package"]
    assert isinstance(context.registry, dict)
    verified_registry = copy.deepcopy(context.registry)
    verified_registry["packages"][0]["review"].update(
        state="verified",
        reviewerRef="synthetic://reviewer",
        evidenceRefs=["synthetic://review"],
    )
    verified_context = replace(context, registry=verified_registry)
    cataloged = evaluate_scope(intake, package, registry_context=verified_context)
    assert cataloged.payload["coverage"]["status"] == "pending_specialist"
    assert cataloged.payload["coverage"]["reasons"] == ["rule_provenance_unverified"]
    assert {line.key for line in cataloged.proposal.lines} == {need.key for need in intake.needs}
    assert not cataloged.payload["commercialReady"]  # catalog status is not technical approval
    mismatch = evaluate_scope(
        intake,
        replace(package, registry_package_id="catalog:other"),
        registry_context=verified_context,
    )
    assert mismatch.proposal.status == "pending_specialist"
    assert mismatch.payload["coverage"]["reasons"] == ["pattern_package_mismatch"]
    wrong_project = evaluate_scope(
        intake,
        package,
        registry_context=replace(
            verified_context,
            project=json.loads((ROOT / "fixtures/valid/painting.json").read_text()),
        ),
    )
    assert wrong_project.payload["coverage"]["reasons"] == ["project_mismatch"]


def test_second_domain_uses_same_coverage_contract_without_assumed_quantity() -> None:
    context = registry_context()
    painting_project = json.loads((ROOT / "fixtures/valid/painting.json").read_text())
    assert isinstance(context.registry, dict)
    registry = copy.deepcopy(context.registry)
    item = registry["packages"][0]
    item["id"] = "catalog:painting-v1"
    item["namespace"] = "example.painting"
    item["applicability"]["categories"] = ["fictional-paint"]
    item["applicability"]["scopes"] = [{"kind": "project", "id": "painting:project"}]
    item["categorySpecs"][0]["category"] = "fictional-paint"
    item["installationPatterns"][0]["category"] = "fictional-paint"
    item["review"].update(
        state="verified",
        reviewerRef="synthetic://reviewer",
        evidenceRefs=["synthetic://review"],
    )
    painting_intake = ProjectIntake(
        "painting:goal",
        "synthetic_painting",
        "TEST-ZONE-A",
        "Pintar superficie ficticia",
        (Need("paint_surface", None, "m2"),),
    )
    painting_package = KnowledgePackage(
        "synthetic_painting",
        "1.0.0",
        "TEST-ZONE-A",
        "synthetic pattern",
        (
            Rule(
                "paint-rule",
                "paint_surface",
                "surface_prep",
                "service",
                "prep",
                "REQUIRES",
                "synthetic",
                quantity_mode="pending",
                unit="service",
            ),
        ),
        registry_package_id="catalog:painting-v1",
    )
    result = evaluate_scope(
        painting_intake,
        painting_package,
        registry_context=RegistryContext(
            painting_project,
            registry,
            "fictional-paint",
            {"kind": "project", "id": "painting:project"},
        ),
    )
    assert result.payload["coverage"]["status"] == "pending_specialist"
    assert result.payload["coverage"]["reasons"] == ["rule_provenance_unverified"]
    assert result.payload["lines"][0]["quantity"] is None
    assert len(result.payload["lines"]) == 1
    assert not result.payload["commercialReady"]
