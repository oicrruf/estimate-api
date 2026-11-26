"""Typed, conservative adapter over AT-238's confirmed-route evaluator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, cast

from estimate_api.hardware.evaluate import evaluate_route


@dataclass(frozen=True)
class HardwareLine:
    material_id: str
    family: str
    quantity: int
    unit: str
    rule_id: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class HardwareGap:
    family: str
    quantity: int
    rule_id: str
    evidence_ids: tuple[str, ...]
    alternatives: tuple[str, ...]


@dataclass(frozen=True)
class HardwareScope:
    status: Literal["PENDING", "REVIEW_REQUIRED", "DERIVED"]
    lines: tuple[HardwareLine, ...]
    missing: tuple[HardwareGap, ...]
    incompatible: tuple[str, ...]
    pending: tuple[str, ...]
    professional_validation_required: bool


def evaluate_hardware_scope(catalog: dict[str, Any], route: dict[str, Any]) -> HardwareScope:
    """Keep unconfirmed routes empty; never promote alternatives into material lines."""
    raw = evaluate_route(catalog, route)
    status = raw["status"]
    if status not in ("PENDING", "REVIEW_REQUIRED", "DERIVED"):
        raise ValueError("Unknown AT-238 status")
    lines = tuple(
        HardwareLine(
            material_id=str(item["material_id"]),
            family=str(item["family"]),
            quantity=item["quantity"],
            unit=str(item["unit"]),
            rule_id=str(item["rule_id"]),
            evidence_ids=tuple(item["evidence_ids"]),
        )
        for item in raw["lines"]
    )
    gaps = tuple(
        HardwareGap(
            family=str(item["family"]),
            quantity=item["quantity"],
            rule_id=str(item["ruleId"]),
            evidence_ids=tuple(item["evidenceIds"]),
            alternatives=tuple(str(option["id"]) for option in item["alternatives"]),
        )
        for item in raw["missing"]
    )
    if status == "PENDING" and (lines or gaps or raw["incompatible"]):
        raise ValueError("Pending route cannot carry material counts")
    return HardwareScope(
        status=cast(Literal["PENDING", "REVIEW_REQUIRED", "DERIVED"], status),
        lines=lines,
        missing=gaps,
        incompatible=tuple(str(item["id"]) for item in raw["incompatible"]),
        pending=tuple(str(item) for item in raw["pending"]),
        professional_validation_required=bool(raw["professionalValidationRequired"]),
    )
