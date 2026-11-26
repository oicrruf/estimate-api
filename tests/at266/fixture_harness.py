"""AT-266 test-only typed seam for future AT-240 discovery integration.

These synthetic fixture rules are not installation guidance or production discovery.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal, TypedDict, cast

from estimate_api.contracts.universal_v1 import ProjectDocument, Scope, validate_project_document
from estimate_api.knowledge.registry_v1 import Registry, validate_registry

ROOT = Path(__file__).resolve().parents[2]


class Seed(TypedDict):
    item: str
    quantity: int | float
    unit: str


class FixtureRule(TypedDict):
    id: str
    packageId: str
    trigger: str
    output: str
    factor: int | float
    unit: str
    mode: Literal["per_unit", "fixed"]


class FixtureCase(TypedDict):
    fixtureVersion: Literal["1.0.0"]
    synthetic: Literal[True]
    brief: str
    itemLabels: dict[str, str]
    projectFile: str
    jurisdiction: str
    category: str
    scope: Scope
    seed: Seed
    changedSeedQuantity: int | float
    rules: list[FixtureRule]


class DiscoveryInput(TypedDict):
    """Common handoff shape; AT-240 may adapt this after its branch integrates."""

    project: ProjectDocument
    registry: Registry
    jurisdiction: str
    category: str
    scope: Scope
    seed: Seed
    rules: list[FixtureRule]


def load_case(name: str) -> tuple[FixtureCase, DiscoveryInput]:
    case = cast(
        FixtureCase,
        json.loads((ROOT / "fixtures" / "at266" / f"{name}.json").read_text()),
    )
    project_value: Any = json.loads((ROOT / case["projectFile"]).read_text())
    registry_value: Any = json.loads((ROOT / "fixtures/at266/registry.json").read_text())
    project_result = validate_project_document(project_value)
    registry_result = validate_registry(registry_value)
    assert project_result.valid, project_result.issues
    assert registry_result.valid, registry_result.issues
    assert project_result.document is not None
    assert registry_result.registry is not None
    assert case["fixtureVersion"] == "1.0.0" and case["synthetic"] is True
    assert case["brief"] and case["itemLabels"]
    return case, {
        "project": project_result.document,
        "registry": registry_result.registry,
        "jurisdiction": case["jurisdiction"],
        "category": case["category"],
        "scope": case["scope"],
        "seed": case["seed"],
        "rules": case["rules"],
    }


def fixture_discovery(value: DiscoveryInput) -> dict[str, tuple[Decimal, str]]:
    """Walk fixture relations generically; return quantities, with no technical approval."""
    project = value["project"]
    registry = value["registry"]
    allowed = {
        package["id"]: package
        for package in registry["packages"]
        if package["namespace"]
        in {ref["namespace"] for ref in project["packages"] if ref["version"] == package["version"]}
        and value["category"] in package["applicability"]["categories"]
        and value["jurisdiction"] in package["applicability"]["jurisdictions"]
        and value["scope"] in package["applicability"]["scopes"]
    }
    rules = []
    for rule in value["rules"]:
        package = allowed.get(rule["packageId"])
        if package is None:
            raise ValueError("rule outside applicable package")
        declarations = [d for group in package["ruleSets"] for d in group["rules"]]
        if not any(
            d["topic"] == rule["id"] and d["choice"] == rule["output"] for d in declarations
        ):
            raise ValueError("rule absent from catalog declaration")
        if rule["factor"] <= 0 or rule["trigger"] == rule["output"]:
            raise ValueError("invalid fixture rule")
        rules.append(rule)
    seed = value["seed"]
    if seed["quantity"] <= 0:
        raise ValueError("invalid seed")
    output: dict[str, tuple[Decimal, str]] = {
        seed["item"]: (Decimal(str(seed["quantity"])), seed["unit"])
    }
    pending = [seed["item"]]
    while pending:
        parent = pending.pop(0)
        for rule in rules:
            if rule["trigger"] != parent:
                continue
            if rule["output"] in output:
                raise ValueError("duplicate or cyclic fixture output")
            quantity = Decimal(str(rule["factor"]))
            if rule["mode"] == "per_unit":
                quantity *= output[parent][0]
            output[rule["output"]] = (quantity, rule["unit"])
            pending.append(rule["output"])
    return output
