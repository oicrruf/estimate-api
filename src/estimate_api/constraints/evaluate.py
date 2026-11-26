"""Evaluate declarative checks without domain-specific engineering assumptions."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Literal, cast

from estimate_api.contracts.universal_v1 import ProjectDocument, validate_project_document

NAMESPACE = "estimate.constraints"
VERSION = "1.0.0"
type FindingStatus = Literal["pass", "fail", "pending"]
type CheckKind = Literal["cardinality", "capacity", "compatibility", "coverage"]


@dataclass(frozen=True)
class SourceRef:
    entity_id: str
    revision: int
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class Finding:
    check_id: str
    kind: CheckKind | str
    status: FindingStatus
    blocking: bool
    reason: str
    subject_id: str
    package_id: str
    sources: tuple[SourceRef, ...]


def _claim(value: object, entities: dict[str, dict[str, object]]) -> tuple[object, SourceRef]:
    if not isinstance(value, dict) or set(value) != {"value", "source"}:
        raise ValueError("claim requires value and source")
    source = value["source"]
    if not isinstance(source, dict) or set(source) != {"entityId", "revision", "evidenceIds"}:
        raise ValueError("claim requires complete source")
    entity_id = source["entityId"]
    revision = source["revision"]
    evidence_ids = source["evidenceIds"]
    if not isinstance(entity_id, str) or entity_id not in entities:
        raise ValueError("claim source entity is missing")
    entity = entities[entity_id]
    if type(revision) is not int or revision != entity["revision"]:
        raise ValueError("claim source revision is stale or missing")
    if entity["knowledgeState"] != "known":
        raise ValueError("claim source is not known")
    if (
        not isinstance(evidence_ids, list)
        or not evidence_ids
        or any(
            not isinstance(item, str)
            or item not in entities
            or entities[item]["kind"] != "Evidence"
            or entities[item]["knowledgeState"] != "known"
            or {"predicate": "supports", "targetId": entity_id}
            not in cast(list[object], entities[item].get("relations", []))
            for item in evidence_ids
        )
    ):
        raise ValueError("claim evidence chain is missing or not known")
    return value["value"], SourceRef(entity_id, revision, tuple(evidence_ids))


def _number(value: object, integer: bool) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        raise ValueError("quantity must be numeric")
    try:
        number = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("quantity must be numeric") from exc
    if not number.is_finite() or number < 0 or (integer and number != number.to_integral_value()):
        raise ValueError("quantity must be finite, nonnegative, and integral for cardinality")
    return number


def _strings(value: object) -> set[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ValueError("set claim must contain nonempty strings")
    return set(value)


def _evaluate(
    check: Mapping[str, object], entities: dict[str, dict[str, object]]
) -> tuple[bool, tuple[SourceRef, ...]]:
    kind = check["kind"]
    inputs = check["inputs"]
    if not isinstance(inputs, dict):
        raise ValueError("inputs must be an object")
    keys = {
        "cardinality": {"demand", "limit", "unit"},
        "capacity": {"demand", "limit", "unit"},
        "compatibility": {"selected", "allowed"},
        "coverage": {"required", "provided"},
    }
    if not isinstance(kind, str) or kind not in keys or set(inputs) != keys[kind]:
        raise ValueError("unsupported check or incomplete inputs")
    if kind in ("cardinality", "capacity"):
        unit = inputs["unit"]
        if not isinstance(unit, str) or not unit:
            raise ValueError("unit is required")
        demand, demand_ref = _claim(inputs["demand"], entities)
        limit, limit_ref = _claim(inputs["limit"], entities)
        return _number(demand, kind == "cardinality") <= _number(limit, kind == "cardinality"), (
            demand_ref,
            limit_ref,
        )
    if kind == "compatibility":
        selected, selected_ref = _claim(inputs["selected"], entities)
        allowed, allowed_ref = _claim(inputs["allowed"], entities)
        if not isinstance(selected, str) or not selected:
            raise ValueError("selected model must be a nonempty string")
        return selected in _strings(allowed), (selected_ref, allowed_ref)
    required, required_ref = _claim(inputs["required"], entities)
    provided, provided_ref = _claim(inputs["provided"], entities)
    return _strings(required) <= _strings(provided), (required_ref, provided_ref)


def evaluate_global_constraints(document: ProjectDocument) -> tuple[Finding, ...]:
    """Return one finding per constraint package; unknown evidence blocks approval."""
    validated = validate_project_document(document)
    if not validated.valid:
        raise ValueError(f"invalid project document: {validated.issues}")
    entities = {entity["id"]: cast(dict[str, object], entity) for entity in document["entities"]}
    findings: list[Finding] = []
    for package in document["packages"]:
        if package["namespace"] != NAMESPACE:
            continue
        facts = package["facts"]
        check = facts.get("check")
        kind: str = "unknown"
        check_id = package["id"]
        status: FindingStatus = "pending"
        reason = "missing or unverified critical evidence"
        sources: tuple[SourceRef, ...] = ()
        try:
            if (
                package["version"] != VERSION
                or entities[package["subjectId"]]["kind"] != "Constraint"
            ):
                raise ValueError("unsupported package version or subject kind")
            if entities[package["subjectId"]]["knowledgeState"] != "known":
                raise ValueError("constraint is not known")
            if not isinstance(check, dict) or set(check) != {"id", "kind", "inputs"}:
                raise ValueError("check envelope is incomplete")
            if not isinstance(check["id"], str) or not check["id"]:
                raise ValueError("check id is required")
            check_id = check["id"]
            kind = str(check["kind"])
            passed, sources = _evaluate(check, entities)
            status = "pass" if passed else "fail"
            reason = "satisfied" if passed else "constraint violated"
        except (ValueError, KeyError, TypeError) as exc:
            reason = str(exc)
        findings.append(
            Finding(
                check_id,
                kind,
                status,
                status != "pass",
                reason,
                package["subjectId"],
                package["id"],
                sources,
            )
        )
    return tuple(findings)
