"""Bounded discovery and explicit scope review; never performs purchasing."""

from __future__ import annotations

from dataclasses import replace
from math import isfinite
from typing import Literal

from .models import (
    KnowledgePackage,
    LineState,
    PatternProvider,
    ProjectIntake,
    Proposal,
    ProposalLine,
    ReviewAction,
    Rule,
    RuleOrigin,
    WorkState,
)

RELATIONS = {
    "REQUIRES",
    "DEPENDS_ON",
    "CONNECTS_TO",
    "INSTALLED_WITH",
    "TERMINATES_AT",
    "REQUIRES_POWER",
    "MOUNTED_ON",
}


def _positive_finite(value: float | None) -> bool:
    if value is None or isinstance(value, bool) or not isinstance(value, int | float):
        return False
    try:
        return value > 0 and isfinite(value)
    except OverflowError:
        return False


def _derived_quantity(parent_qty: float | None, rule: Rule) -> float | None:
    if rule.quantity_mode == "pending":
        quantity = None
    elif rule.quantity_mode == "same":
        quantity = parent_qty
    elif rule.quantity_mode == "fixed":
        quantity = rule.factor
    else:
        try:
            quantity = (
                parent_qty * rule.factor
                if parent_qty is not None and rule.factor is not None
                else None
            )
        except OverflowError as error:
            raise ValueError(f"Invalid derived quantity in {rule.id}") from error
    if quantity is not None and not _positive_finite(quantity):
        raise ValueError(f"Invalid derived quantity in {rule.id}")
    return quantity


def _would_cycle(paths: list[tuple[str, str, str]], source: str, target: str) -> bool:
    """Check the whole discovered graph before adding a cross-branch edge."""
    adjacency: dict[str, set[str]] = {}
    for origin, _, destination in paths:
        adjacency.setdefault(origin, set()).add(destination)
    pending = [target]
    visited: set[str] = set()
    while pending:
        current = pending.pop()
        if current == source:
            return True
        if current not in visited:
            visited.add(current)
            pending.extend(adjacency.get(current, set()) - visited)
    return False


def attach_lineage(proposal: Proposal, edges: tuple[tuple[str, str, str], ...]) -> Proposal:
    """Add verified lineage for review invalidation without recalculating quantities."""
    paths = list(proposal.evidence_paths)
    known = {line.key for line in proposal.lines}
    for source, relation, target in edges:
        edge = (source, relation, target)
        if source not in known or target not in known:
            raise ValueError("Pattern lineage references an absent candidate")
        if edge not in paths:
            if _would_cycle(paths, source, target):
                raise ValueError("Pattern lineage cycle")
            paths.append(edge)
    return replace(proposal, evidence_paths=tuple(paths))


def _package(
    intake: ProjectIntake, provider: PatternProvider | KnowledgePackage | None
) -> KnowledgePackage | None:
    package = (
        provider
        if isinstance(provider, KnowledgePackage) or provider is None
        else provider.get(intake.domain, intake.jurisdiction)
    )
    if (
        package is None
        or package.domain != intake.domain
        or package.jurisdiction != intake.jurisdiction
    ):
        return None
    if not package.version or not package.source:
        raise ValueError("Knowledge package needs version and source")
    ids = [rule.id for rule in package.rules]
    if len(ids) != len(set(ids)) or any(rule.relation not in RELATIONS for rule in package.rules):
        raise ValueError("Duplicate rule ID or unsupported relation")
    return package


def _status(
    lines: tuple[ProposalLine, ...], specialist: bool = False
) -> Literal["proposed", "approved", "blocked", "pending_specialist"]:
    if specialist:
        return "pending_specialist"
    if any(line.required and line.state == "rejected" for line in lines):
        return "blocked"
    if all(line.state in ("user_requested", "user_approved", "rejected") for line in lines) and all(
        line.quantity is not None for line in lines if line.required
    ):
        return "approved"
    return "proposed"


def _summarize(lines: tuple[ProposalLine, ...]) -> dict[str, WorkState]:
    groups: dict[str, list[ProposalLine]] = {}
    for line in lines:
        groups.setdefault(line.work_package, []).append(line)
    return {
        group: (
            "incomplete"
            if any(item.required and item.state == "rejected" for item in items)
            else "pending"
            if any(
                item.required
                and (item.quantity is None or item.state not in ("user_requested", "user_approved"))
                for item in items
            )
            else "complete"
        )
        for group, items in groups.items()
    }


def discover(
    intake: ProjectIntake,
    provider: PatternProvider | KnowledgePackage | None,
    *,
    max_depth: int = 6,
    max_lines: int = 100,
) -> Proposal:
    if max_depth < 0 or max_lines < 1 or not intake.project_id or not intake.goal:
        raise ValueError("Invalid discovery bounds or intake")
    if not intake.needs or any(
        need.quantity is not None and not _positive_finite(need.quantity) for need in intake.needs
    ):
        raise ValueError("Intake needs positive or pending quantities")
    package = _package(intake, provider)
    lines = {
        need.key: ProposalLine(
            need.key,
            None,
            "requested",
            need.quantity,
            need.unit,
            "user_requested",
            True,
            "Declarado por el usuario",
            None,
            None,
            None,
            None,
            None,
            None,
        )
        for need in intake.needs
    }
    if len(lines) != len(intake.needs) or len(lines) > max_lines:
        raise ValueError("Duplicate need or line limit")
    if package is None or not any(rule.source_key in lines for rule in package.rules):
        return Proposal(
            intake.project_id,
            1,
            "pending_specialist",
            tuple(lines.values()),
            ("Falta un paquete de conocimiento validado para este rubro y jurisdicción.",),
            {"requested": "pending"},
            (),
            commercial_ready=False,
        )
    rules_by_source: dict[str, list[Rule]] = {}
    for rule in package.rules:
        rules_by_source.setdefault(rule.source_key, []).append(rule)
    queue: list[tuple[str, int, tuple[str, ...]]] = [(key, 0, (key,)) for key in lines]
    paths: list[tuple[str, str, str]] = []
    questions: list[str] = []
    blocking_facts: set[str] = set()
    requested_incoming: dict[str, int] = {}
    while queue:
        source, depth, ancestors = queue.pop(0)
        for rule in sorted(rules_by_source.get(source, []), key=lambda item: item.id):
            if rule.when_fact is not None and rule.when_fact not in intake.facts:
                blocking_facts.add(rule.when_fact)
                continue
            if rule.when_fact is not None and intake.facts.get(rule.when_fact) != rule.when_value:
                continue
            if rule.target_key in ancestors:
                raise ValueError(f"Pattern cycle at {rule.id}")
            if depth >= max_depth:
                raise ValueError("Pattern depth limit")
            origin = RuleOrigin(
                source,
                rule.id,
                rule.pattern_id,
                rule.evidence_ids,
                rule.rule_ids,
                rule.source_refs,
                rule.candidate_paths,
            )
            quantity = _derived_quantity(lines[source].quantity, rule)
            if rule.target_key in lines:
                if _would_cycle(paths, source, rule.target_key):
                    raise ValueError(f"Pattern cycle at {rule.id}")
                paths.append((source, rule.relation, rule.target_key))
                prior = lines[rule.target_key]
                lines[rule.target_key] = replace(
                    prior,
                    required=prior.required or rule.required,
                    evidence_ids=tuple(dict.fromkeys((*prior.evidence_ids, *rule.evidence_ids))),
                    rule_ids=tuple(dict.fromkeys((*prior.rule_ids, *rule.rule_ids))),
                    source_refs=tuple(dict.fromkeys((*prior.source_refs, *rule.source_refs))),
                    candidate_paths=tuple(
                        dict.fromkeys((*prior.candidate_paths, *rule.candidate_paths))
                    ),
                    rule_provenance=(*prior.rule_provenance, origin),
                )
                if prior.state == "user_requested":
                    requested_incoming[rule.target_key] = (
                        requested_incoming.get(rule.target_key, 0) + 1
                    )
                    quantity_conflict = requested_incoming[rule.target_key] > 1
                else:
                    quantity_conflict = prior.parent_key != source
                if (
                    quantity_conflict
                    or quantity is None
                    or prior.quantity != quantity
                    or prior.unit != rule.unit
                ):
                    blocking_facts.add(f"quantity:{rule.target_key}")
                    questions.append(
                        f"¿Qué cantidad total de {rule.target_key} cubre todas las dependencias?"
                    )
                continue
            if len(lines) >= max_lines:
                raise ValueError("Pattern line limit")
            state: LineState = "pending_measurement" if quantity is None else "agent_proposed"
            lines[rule.target_key] = ProposalLine(
                rule.target_key,
                rule.kind,
                rule.work_package,
                quantity,
                rule.unit,
                state,
                rule.required,
                f"{source} {rule.relation} {rule.target_key}",
                rule.id,
                f"{package.source} | {rule.evidence}",
                package.version,
                package.jurisdiction,
                source,
                rule.relation,
                rule.evidence_ids,
                rule.rule_ids,
                rule.source_refs,
                rule.candidate_paths,
                rule.pattern_id,
                (origin,),
            )
            paths.append((source, rule.relation, rule.target_key))
            if quantity is None:
                questions.append(
                    rule.question or f"¿Qué cantidad de {rule.target_key} se requiere?"
                )
            queue.append((rule.target_key, depth + 1, (*ancestors, rule.target_key)))
    result_lines = tuple(lines.values())
    reached = {target for _, _, target in paths}
    uncovered_needs = tuple(
        need.key
        for need in intake.needs
        if not rules_by_source.get(need.key) and need.key not in reached
    )
    questions.extend(
        f"¿Cuál es el valor confirmado de {fact}?"
        for fact in sorted(blocking_facts)
        if not fact.startswith("quantity:")
    )
    questions.extend(
        f"Falta cobertura especializada para {key}. ¿Quién valida esta necesidad?"
        for key in uncovered_needs
    )
    base_status = _status(result_lines)
    status = (
        "pending_specialist"
        if uncovered_needs
        else "proposed"
        if blocking_facts and base_status == "approved"
        else base_status
    )
    return Proposal(
        intake.project_id,
        1,
        status,
        result_lines,
        tuple(dict.fromkeys(questions)),
        _summarize(result_lines),
        tuple(paths),
        blocking_facts=tuple(sorted(blocking_facts)),
        commercial_ready=status == "approved",
    )


def review(proposal: Proposal, actions: tuple[ReviewAction, ...]) -> Proposal:
    if proposal.status == "pending_specialist":
        raise ValueError("Specialist coverage is required")
    decisions = {action.key: action for action in actions}
    if len(decisions) != len(actions):
        raise ValueError("Duplicate review action")
    known = {line.key for line in proposal.lines}
    if not decisions.keys() <= known:
        raise ValueError("Unknown proposal line")
    descendants: set[str] = set()
    modified = {action.key for action in actions if action.decision == "modify"}
    frontier = set(modified)
    while frontier:
        children = {
            target
            for source, _, target in proposal.evidence_paths
            if source in frontier and target not in modified and target not in descendants
        }
        descendants.update(children)
        frontier = children
    requested_descendants = {
        line.key
        for line in proposal.lines
        if line.key in descendants and line.state == "user_requested"
    }
    updated = []
    for line in proposal.lines:
        action = decisions.get(line.key)
        if line.key in descendants:
            if action is not None:
                raise ValueError("Review descendants after parent quantity or unit changes")
            updated.append(
                line
                if line.key in requested_descendants
                else replace(line, quantity=None, state="pending_measurement")
            )
        elif action is None:
            updated.append(line)
        elif line.state == "user_requested":
            raise ValueError("Change requested needs via project intake")
        elif action.decision == "modify":
            if not _positive_finite(action.quantity) or not action.unit:
                raise ValueError("Modification needs positive quantity and unit")
            updated.append(
                replace(line, quantity=action.quantity, unit=action.unit, state="agent_proposed")
            )
        else:
            if action.decision == "approve" and line.quantity is None:
                raise ValueError("Measure quantity before approval")
            updated.append(
                replace(line, state="user_approved" if action.decision == "approve" else "rejected")
            )
    result_lines = tuple(updated)
    blocking_facts = tuple(
        dict.fromkeys(
            (
                *(
                    fact
                    for fact in proposal.blocking_facts
                    if not (
                        fact.startswith("quantity:") and fact.removeprefix("quantity:") in modified
                    )
                ),
                *(f"quantity:{key}" for key in sorted(requested_descendants)),
            )
        )
    )
    confirmed_questions = {
        f"¿Qué cantidad total de {key} cubre todas las dependencias?"
        for key in modified
        if f"quantity:{key}" in proposal.blocking_facts
    }
    base_status = _status(result_lines)
    status = (
        "blocked"
        if proposal.technical_blockers
        else "proposed"
        if blocking_facts and base_status == "approved"
        else base_status
    )
    return replace(
        proposal,
        revision=proposal.revision + 1,
        status=status,
        lines=result_lines,
        work_packages=_summarize(result_lines),
        blocking_facts=blocking_facts,
        questions=tuple(
            dict.fromkeys(
                (
                    *(
                        question
                        for question in proposal.questions
                        if question not in confirmed_questions
                    ),
                    *(f"Confirmar cantidad de {key}" for key in sorted(descendants)),
                )
            )
        ),
        commercial_ready=status == "approved",
    )


def revalidate(
    previous: Proposal, intake: ProjectIntake, provider: PatternProvider | KnowledgePackage | None
) -> Proposal:
    if previous.project_id != intake.project_id:
        raise ValueError("Project mismatch")
    from .trusted import resolve_reviewed_package

    supplied = (
        provider
        if isinstance(provider, KnowledgePackage) or provider is None
        else provider.get(intake.domain, intake.jurisdiction)
    )
    trusted, trust_reason = resolve_reviewed_package(intake, supplied, None)
    fresh = discover(intake, trusted)
    if previous.constraint_check_ids:
        from .constraint_adapter import assess_constraints, attach_constraints

        fresh = attach_constraints(fresh, assess_constraints(None, previous.constraint_check_ids))
    # Standalone rediscovery has no registry context that could verify coverage.
    questions = (*fresh.questions, "Specialist coverage requires verification")
    if trust_reason is not None:
        questions = (*questions, trust_reason)
    fresh = replace(
        fresh,
        status="pending_specialist",
        questions=tuple(dict.fromkeys(questions)),
        commercial_ready=False,
    )
    return diff_proposals(previous, fresh)


def diff_proposals(previous: Proposal, fresh: Proposal) -> Proposal:
    """Invalidate prior review whenever the derived scope is recomputed."""
    if previous.project_id != fresh.project_id:
        raise ValueError("Project mismatch")
    old = {line.key: line for line in previous.lines}
    new = {line.key: line for line in fresh.lines}
    changes = []
    for key in sorted(old.keys() | new.keys()):
        if key not in old:
            changes.append((key, "added"))
        elif key not in new:
            changes.append((key, "removed"))
        elif (
            old[key].quantity != new[key].quantity
            or old[key].unit != new[key].unit
            or old[key].rule_id != new[key].rule_id
        ):
            changes.append((key, "changed"))
        elif old[key].state == "user_approved":
            changes.append((key, "approval_stale"))
    # Re-discovery invalidates all prior approvals and downstream commercial scenarios.
    return replace(
        fresh, revision=previous.revision + 1, changes=tuple(changes), commercial_ready=False
    )
