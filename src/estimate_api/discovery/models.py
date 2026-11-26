"""Contracts shared by discovery and future specialist/accessory packages."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

LineKind = Literal["equipment", "material", "accessory", "consumable", "service"]
LineState = Literal[
    "user_requested", "agent_proposed", "user_approved", "rejected", "pending_measurement"
]
WorkState = Literal["complete", "incomplete", "pending"]


@dataclass(frozen=True)
class Need:
    key: str
    quantity: float | None
    unit: str


@dataclass(frozen=True)
class ProjectIntake:
    project_id: str
    domain: str
    jurisdiction: str
    goal: str
    needs: tuple[Need, ...]
    facts: dict[str, str | int | float | bool] = field(default_factory=dict)
    assumptions: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Rule:
    id: str
    source_key: str
    target_key: str
    kind: LineKind | None
    work_package: str
    relation: str
    evidence: str
    required: bool = True
    quantity_mode: Literal["same", "multiply", "fixed", "pending"] = "pending"
    factor: float | None = None
    unit: str = "each"
    question: str | None = None
    when_fact: str | None = None
    when_value: str | int | float | bool | None = None
    evidence_ids: tuple[str, ...] = ()
    rule_ids: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    candidate_paths: tuple[tuple[str, ...], ...] = ()
    pattern_id: str | None = None


@dataclass(frozen=True)
class KnowledgePackage:
    domain: str
    version: str
    jurisdiction: str
    source: str
    rules: tuple[Rule, ...]
    registry_package_id: str | None = None
    pattern_refs: tuple[tuple[str, str, str], ...] = ()


class PatternProvider(Protocol):
    """Adapter boundary for AT-238/239 and other versioned specialist packages."""

    def get(self, domain: str, jurisdiction: str) -> KnowledgePackage | None: ...


@dataclass(frozen=True)
class RuleOrigin:
    parent_key: str
    rule_id: str
    pattern_id: str | None
    evidence_ids: tuple[str, ...]
    rule_ids: tuple[str, ...]
    source_refs: tuple[str, ...]
    candidate_paths: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class ProposalLine:
    key: str
    kind: LineKind | None
    work_package: str
    quantity: float | None
    unit: str
    state: LineState
    required: bool
    justification: str
    rule_id: str | None
    source: str | None
    package_version: str | None
    jurisdiction: str | None
    parent_key: str | None
    relation: str | None
    evidence_ids: tuple[str, ...] = ()
    rule_ids: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    candidate_paths: tuple[tuple[str, ...], ...] = ()
    pattern_id: str | None = None
    rule_provenance: tuple[RuleOrigin, ...] = ()


@dataclass(frozen=True)
class ReviewAction:
    key: str
    decision: Literal["approve", "reject", "modify"]
    quantity: float | None = None
    unit: str | None = None


@dataclass(frozen=True)
class Proposal:
    project_id: str
    revision: int
    status: Literal["proposed", "approved", "blocked", "pending_specialist"]
    lines: tuple[ProposalLine, ...]
    questions: tuple[str, ...]
    work_packages: dict[str, WorkState]
    evidence_paths: tuple[tuple[str, str, str], ...]
    changes: tuple[tuple[str, str], ...] = ()
    blocking_facts: tuple[str, ...] = ()
    technical_blockers: tuple[str, ...] = ()
    commercial_ready: bool = False
    constraint_check_ids: tuple[str, ...] = ()
