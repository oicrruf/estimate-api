"""Synthetic AT-266 examples; no claim of AT-240 production integration."""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal

import pytest

from estimate_api.knowledge.registry_v1 import resolve_coverage
from tests.at266.fixture_harness import fixture_discovery, load_case

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


@pytest.mark.parametrize(
    "name,other",
    [("cameras", "painting"), ("cameras", "event"), ("painting", "event"), ("event", "cameras")],
)
def test_cross_domain_rules_rejected(name: str, other: str) -> None:
    _, value = load_case(name)
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
