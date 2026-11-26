"""Turn AT-247 bounded candidates into reviewable AT-240 pattern rules."""

from __future__ import annotations

from dataclasses import dataclass

from estimate_api.patterns.v1 import Fact, Pattern, expand

from .models import KnowledgePackage, ProjectIntake, Rule


@dataclass(frozen=True)
class PatternBinding:
    need_key: str
    pattern: Pattern
    facts: dict[str, Fact]


@dataclass(frozen=True)
class PatternPlan:
    package: KnowledgePackage
    pending: tuple[str, ...]
    limit_reached: bool
    professional_validation_required: bool


def build_pattern_plan(
    intake: ProjectIntake,
    bindings: tuple[PatternBinding, ...],
    *,
    registry_package_id: str,
    source: str,
) -> PatternPlan:
    """Only confirmed AT-247 facts create candidates; no product is selected."""
    if not bindings or not registry_package_id or not source:
        raise ValueError("Pattern package requires bindings, registry identity and source")
    requested = {need.key for need in intake.needs}
    if len({binding.need_key for binding in bindings}) != len(bindings):
        raise ValueError("One pattern binding per requested need is required")
    rules: list[Rule] = []
    pending: set[str] = set()
    limited = False
    versions = {binding.pattern["version"] for binding in bindings}
    if len(versions) != 1:
        raise ValueError("Pattern versions must match")
    for binding in bindings:
        if binding.need_key not in requested:
            raise ValueError(f"Pattern root not requested: {binding.need_key}")
        expansion = expand(binding.pattern, binding.facts)
        pending.update(f"{binding.need_key}:{key}" for key in expansion.pending)
        limited |= expansion.status == "LIMIT_REACHED"
        for candidate in expansion.candidates:
            rules.append(
                Rule(
                    id=f"{binding.pattern['id']}/{candidate['itemId']}",
                    source_key=binding.need_key,
                    target_key=candidate["itemId"],
                    kind=None,
                    work_package=binding.pattern["category"],
                    relation="REQUIRES",
                    evidence=f"AT-247 candidate; {binding.pattern['sourceRef']}",
                    quantity_mode="multiply",
                    factor=candidate["quantity"],
                    unit="candidate",
                    evidence_ids=tuple(candidate["evidenceIds"]),
                    rule_ids=tuple(candidate["ruleIds"]),
                    source_refs=tuple(candidate["sourceRefs"]),
                    candidate_paths=tuple(tuple(path) for path in candidate["paths"]),
                    pattern_id=binding.pattern["id"],
                )
            )
    package = KnowledgePackage(
        domain=intake.domain,
        version=next(iter(versions)),
        jurisdiction=intake.jurisdiction,
        source=source,
        rules=tuple(rules),
        registry_package_id=registry_package_id,
        pattern_refs=tuple(
            (binding.pattern["id"], binding.pattern["category"], binding.pattern["sourceRef"])
            for binding in bindings
        ),
    )
    return PatternPlan(package, tuple(sorted(pending)), limited, True)
