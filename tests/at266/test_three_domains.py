"""Synthetic AT-266 examples and the real AT-240 service boundary."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from decimal import Decimal

import pytest

from estimate_api.discovery.engine import revalidate
from estimate_api.discovery.models import KnowledgePackage, Need, ProjectIntake, Proposal
from estimate_api.discovery.registry_adapter import RegistryContext
from estimate_api.discovery.service import evaluate_scope
from estimate_api.discovery.trusted import reviewed_package
from estimate_api.knowledge.registry_v1 import resolve_coverage
from tests.at266.fixture_harness import DiscoveryInput, FixtureCase, fixture_discovery, load_case

EXPECTED = {
    "cameras": (
        {
            "camera:camera": (8, "each"),
            "camera:link": (8, "each"),
            "camera:termination": (16, "each"),
            "camera:conduit": (40, "m"),
            "camera:mount": (8, "each"),
        },
        {
            "camera:camera": (10, "each"),
            "camera:link": (10, "each"),
            "camera:termination": (20, "each"),
            "camera:conduit": (50, "m"),
            "camera:mount": (10, "each"),
        },
    ),
    "painting": (
        {
            "painting:area": (60, "m2"),
            "painting:coat": (120, "m2"),
            "painting:paint": (12, "L"),
            "painting:masking": (2, "roll"),
        },
        {
            "painting:area": (80, "m2"),
            "painting:coat": (160, "m2"),
            "painting:paint": (16, "L"),
            "painting:masking": (2, "roll"),
        },
    ),
    "event": (
        {
            "event:speaker": (4, "each"),
            "event:cable": (4, "each"),
            "event:stand": (4, "each"),
            "event:mixer": (1, "each"),
            "event:technician": (2, "person"),
            "event:power-load": (400, "W"),
        },
        {
            "event:speaker": (6, "each"),
            "event:cable": (6, "each"),
            "event:stand": (6, "each"),
            "event:mixer": (1, "each"),
            "event:technician": (2, "person"),
            "event:power-load": (600, "W"),
        },
    ),
}


def service_input(
    case: FixtureCase, value: DiscoveryInput
) -> tuple[ProjectIntake, KnowledgePackage, RegistryContext]:
    """Map AT-266's validated input without copying or interpreting any rules."""
    package = reviewed_package(case["rules"][0]["packageId"])
    seed = value["seed"]
    intake = ProjectIntake(
        value["project"]["projectId"],
        package.domain,
        value["jurisdiction"],
        case["brief"],
        (Need(seed["item"], seed["quantity"], seed["unit"]),),
    )
    context = RegistryContext(
        value["project"], value["registry"], value["category"], value["scope"]
    )
    return intake, package, context


def service_lines(proposal: Proposal) -> dict[str, tuple[Decimal, str]]:
    assert all(line.quantity is not None for line in proposal.lines)
    return {
        line.key: (Decimal(str(line.quantity)), line.unit)
        for line in proposal.lines
        if line.quantity is not None
    }


@pytest.mark.parametrize("name", EXPECTED)
def test_missing_lines_and_changed_quantities(name: str) -> None:
    case, value = load_case(name)
    coverage = resolve_coverage(
        value["project"],
        value["registry"],
        jurisdiction=value["jurisdiction"],
        category=value["category"],
        scope=value["scope"],
    )
    assert coverage.status == "pending_specialist"
    assert coverage.reasons == ("unverified_package",)
    assert coverage.package_ids == (case["rules"][0]["packageId"],)
    before, after = EXPECTED[name]
    assert fixture_discovery(value) == {k: (Decimal(v), u) for k, (v, u) in before.items()}
    changed = deepcopy(value)
    changed["seed"]["quantity"] = case["changedSeedQuantity"]
    assert fixture_discovery(changed) == {k: (Decimal(v), u) for k, (v, u) in after.items()}
    assert set(before) - {value["seed"]["item"]}  # missing from initial request

    intake, package, context = service_input(case, value)
    actual = evaluate_scope(intake, package, registry_context=context)
    assert service_lines(actual.proposal) == fixture_discovery(value)
    assert actual.proposal.status == "pending_specialist"
    assert actual.payload["coverage"]["reasons"] == ["unverified_package"]
    assert not actual.payload["commercialReady"]
    changed_intake = replace(
        intake,
        needs=(Need(value["seed"]["item"], case["changedSeedQuantity"], value["seed"]["unit"]),),
    )
    rechecked = revalidate(actual.proposal, changed_intake, package)
    assert service_lines(rechecked) == fixture_discovery(changed)
    assert rechecked.status == "pending_specialist" and not rechecked.commercial_ready
    assert all(line.state != "user_approved" for line in rechecked.lines)


@pytest.mark.parametrize(
    "name,other",
    [("cameras", "painting"), ("cameras", "event"), ("painting", "event"), ("event", "cameras")],
)
def test_cross_domain_rules_rejected(name: str, other: str) -> None:
    case, value = load_case(name)
    other_case, _ = load_case(other)
    contaminated = deepcopy(value)
    contaminated["rules"].append(other_case["rules"][0])
    with pytest.raises(ValueError, match="outside applicable package"):
        fixture_discovery(contaminated)
    other_category = other_case["category"]
    assert (
        resolve_coverage(
            value["project"],
            value["registry"],
            jurisdiction=value["jurisdiction"],
            category=other_category,
            scope=value["scope"],
        ).status
        == "unsupported"
    )
    intake, package, context = service_input(case, value)
    foreign = reviewed_package(other_case["rules"][0]["packageId"]).rules[0]
    injected = replace(package, rules=(*package.rules, foreign))
    scoped = evaluate_scope(intake, injected, registry_context=context)
    assert {line.key for line in scoped.proposal.lines} == {value["seed"]["item"]}
    assert "reviewed_package_mismatch" in scoped.payload["coverage"]["reasons"]
    assert not scoped.payload["commercialReady"]
    previous = evaluate_scope(intake, package, registry_context=context).proposal
    rechecked = revalidate(previous, intake, injected)
    assert {line.key for line in rechecked.lines} == {value["seed"]["item"]}
    assert rechecked.status == "pending_specialist" and not rechecked.commercial_ready


def test_catalog_declaration_and_version_mismatch_block_fixture() -> None:
    _, value = load_case("cameras")
    altered = deepcopy(value)
    altered["rules"][0]["output"] = "camera:unexpected"
    with pytest.raises(ValueError, match="absent from catalog declaration"):
        fixture_discovery(altered)
    altered = deepcopy(value)
    for reference in altered["project"]["packages"]:
        reference["version"] = "2.0.0"
    with pytest.raises(ValueError, match="outside applicable package"):
        fixture_discovery(altered)

    case, value = load_case("cameras")
    intake, package, context = service_input(case, value)
    missing_source = deepcopy(value["registry"])
    missing_source["packages"][0]["ruleSets"][0]["rules"][0]["sourceRef"] = (
        "synthetic://missing-evidence"
    )
    scoped = evaluate_scope(
        intake, package, registry_context=replace(context, registry=missing_source)
    )
    assert {line.key for line in scoped.proposal.lines} == {value["seed"]["item"]}
    assert "reviewed_rule_declaration_missing" in scoped.payload["coverage"]["reasons"]
    assert not scoped.payload["commercialReady"]
    no_check_evidence = evaluate_scope(
        intake,
        package,
        registry_context=context,
        required_constraint_ids=("synthetic:unconfirmed-site-capacity",),
    )
    assert no_check_evidence.proposal.technical_blockers
    assert no_check_evidence.payload["constraints"] is not None
    assert no_check_evidence.payload["constraints"]["status"] == "pending"
    assert not no_check_evidence.payload["commercialReady"]
