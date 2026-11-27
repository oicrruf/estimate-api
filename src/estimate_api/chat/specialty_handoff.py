"""Local AT-246 scope draft to specialist questions; no model or service calls."""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any

from estimate_api.domain.scope_capture import Fact, ScopeDraft, ScopeIntake, build_scope_draft
from estimate_api.specialties.routing import RoutingRequest, RoutingResult, route_specialties


@dataclass(frozen=True)
class SpecialistHandoff:
    scope_draft: ScopeDraft
    routing: RoutingResult
    evidence_reasons: tuple[str, ...]
    persisted: bool = False


@dataclass(frozen=True)
class LocalEvidenceBinding:
    """Caller supplied test binding, not an authenticated evidence receipt."""

    evidence_id: str
    project_id: str
    field: str
    value: Any
    revision: int


def _facts(value: Any, prefix: str) -> tuple[tuple[str, Fact[Any]], ...]:
    if value is None:
        return ()
    return tuple(
        (f"{prefix}.{field.name}", item)
        for field in fields(value)
        if isinstance(item := getattr(value, field.name), Fact)
    )


def preview_specialist_handoff(
    scope: ScopeIntake,
    request: RoutingRequest,
    *,
    evidence_bindings: tuple[LocalEvidenceBinding, ...],
    evidence_revision: int,
    previous: RoutingRequest | None = None,
) -> SpecialistHandoff:
    """Match local typed bindings; their source authenticity is caller-owned."""
    if evidence_revision < 0:
        raise ValueError("evidence revision must be nonnegative")
    draft = build_scope_draft(scope)
    bindings = {binding.evidence_id: binding for binding in evidence_bindings}
    if len(bindings) != len(evidence_bindings) or any(not key.strip() for key in bindings):
        raise ValueError("evidence IDs must be unique and nonempty")
    for field, fact in (
        *_facts(scope, "scope"),
        *_facts(request.cameras, "camera"),
        *(
            pair
            for route in request.raceways
            for pair in _facts(route, f"raceway.{route.route_id}")
        ),
    ):
        if fact.certainty.value != "confirmed":
            continue
        binding = bindings.get(fact.evidence) if fact.evidence is not None else None
        if (
            binding is None
            or binding.project_id != request.project_id
            or binding.field != field
            or binding.revision != evidence_revision
            or type(binding.value) is not type(fact.value)
            or binding.value != fact.value
        ):
            raise ValueError("confirmed fact lacks a matching local evidence binding")
    routing = route_specialties(request, previous=previous)
    reasons = tuple(
        dict.fromkeys(
            reason
            for assignment in routing.assignments
            for reason in assignment.evidence_dependencies
        )
    )
    return SpecialistHandoff(draft, routing, reasons)
