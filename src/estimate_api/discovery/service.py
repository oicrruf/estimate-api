"""Deterministic backend entry point and versioned review payload for A2UI consumers."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal, Protocol, TypedDict

from estimate_api.knowledge.registry_v1 import CoverageResult

from .engine import discover
from .evidence import EvidenceReference
from .hardware_adapter import HardwareScope
from .models import KnowledgePackage, PatternProvider, ProjectIntake, Proposal
from .registry_adapter import RegistryContext, resolve_pattern_coverage

SCHEMA_VERSION: Literal["scope-review.v1"] = "scope-review.v1"


class EvidenceReader(Protocol):
    def resolve(self, evidence_ids: tuple[str, ...]) -> tuple[EvidenceReference, ...]: ...


class EvidencePayload(TypedDict):
    id: str
    status: str
    source: str | None
    capabilityPaths: list[list[str]]


class LinePayload(TypedDict):
    key: str
    kind: str | None
    workPackage: str
    quantity: float | None
    unit: str
    state: str
    required: bool
    justification: str
    ruleId: str | None
    packageVersion: str | None
    jurisdiction: str | None
    source: str | None
    parentKey: str | None
    relation: str | None
    evidence: list[EvidencePayload]
    evidenceStatus: Literal["capability_context", "unknown"]
    actions: list[str]


class ScopeReviewPayload(TypedDict):
    schemaVersion: Literal["scope-review.v1"]
    projectId: str
    revision: int
    status: str
    commercialReady: bool
    lines: list[LinePayload]
    questions: list[str]
    blockingFacts: list[str]
    workPackages: dict[str, str]
    evidencePaths: list[list[str]]
    changes: list[dict[str, str]]
    hardware: HardwarePayload | None
    coverage: CoveragePayload


class CoveragePayload(TypedDict):
    status: str
    packageIds: list[str]
    reasons: list[str]


class HardwarePayload(TypedDict):
    status: str
    lines: list[dict[str, str | int | list[str]]]
    missing: list[dict[str, str | int | list[str]]]
    incompatible: list[str]
    pending: list[str]
    professionalValidationRequired: bool


@dataclass(frozen=True)
class ScopeEvaluation:
    proposal: Proposal
    payload: ScopeReviewPayload


def to_review_payload(
    proposal: Proposal,
    evidence_reader: EvidenceReader | None = None,
    *,
    coverage: CoverageResult | None = None,
    technical_validated: bool = False,
    hardware_scope: HardwareScope | None = None,
) -> ScopeReviewPayload:
    """Render contract data; catalog coverage never implies technical validation."""
    if coverage is None:
        coverage = CoverageResult("pending_specialist", (), (), ("registry_mapping_missing",))
    rendered: list[LinePayload] = []
    evidence_complete = True
    for line in proposal.lines:
        references = (
            evidence_reader.resolve(line.evidence_ids)
            if evidence_reader is not None and line.evidence_ids
            else ()
        )
        status: Literal["capability_context", "unknown"] = (
            "capability_context"
            if references and all(ref.status == "capability_context" for ref in references)
            else "unknown"
        )
        if line.rule_id is not None and status == "unknown":
            evidence_complete = False
        actions = [] if line.state == "user_requested" else ["approve", "reject", "modify"]
        if line.quantity is None and "approve" in actions:
            actions.remove("approve")
        rendered.append(
            LinePayload(
                key=line.key,
                kind=line.kind,
                workPackage=line.work_package,
                quantity=line.quantity,
                unit=line.unit,
                state=line.state,
                required=line.required,
                justification=line.justification,
                ruleId=line.rule_id,
                packageVersion=line.package_version,
                jurisdiction=line.jurisdiction,
                source=line.source,
                parentKey=line.parent_key,
                relation=line.relation,
                evidence=[
                    EvidencePayload(
                        id=ref.id,
                        status=ref.status,
                        source=ref.source,
                        capabilityPaths=[list(path) for path in ref.capability_paths],
                    )
                    for ref in references
                ],
                evidenceStatus=status,
                actions=actions,
            )
        )
    hardware_payload: HardwarePayload | None = None
    if hardware_scope is not None:
        hardware_payload = HardwarePayload(
            status=hardware_scope.status,
            lines=[
                {
                    "materialId": line.material_id,
                    "family": line.family,
                    "quantity": line.quantity,
                    "unit": line.unit,
                    "ruleId": line.rule_id,
                    "evidenceIds": list(line.evidence_ids),
                }
                for line in hardware_scope.lines
            ],
            missing=[
                {
                    "family": gap.family,
                    "quantity": gap.quantity,
                    "ruleId": gap.rule_id,
                    "evidenceIds": list(gap.evidence_ids),
                    "alternatives": list(gap.alternatives),
                }
                for gap in hardware_scope.missing
            ],
            incompatible=list(hardware_scope.incompatible),
            pending=list(hardware_scope.pending),
            professionalValidationRequired=hardware_scope.professional_validation_required,
        )
    hardware_ready = hardware_scope is None or (
        hardware_scope.status == "DERIVED" and not hardware_scope.professional_validation_required
    )
    return ScopeReviewPayload(
        schemaVersion=SCHEMA_VERSION,
        projectId=proposal.project_id,
        revision=proposal.revision,
        status=proposal.status,
        commercialReady=proposal.commercial_ready
        and coverage.status == "cataloged"
        and technical_validated
        and evidence_complete
        and hardware_ready,
        lines=rendered,
        questions=list(proposal.questions),
        blockingFacts=list(proposal.blocking_facts),
        workPackages=dict(proposal.work_packages),
        evidencePaths=[list(path) for path in proposal.evidence_paths],
        changes=[{"key": key, "change": change} for key, change in proposal.changes],
        hardware=hardware_payload,
        coverage=CoveragePayload(
            status=coverage.status,
            packageIds=list(coverage.package_ids),
            reasons=list(coverage.reasons),
        ),
    )


def evaluate_scope(
    intake: ProjectIntake,
    provider: PatternProvider | KnowledgePackage | None,
    evidence_reader: EvidenceReader | None = None,
    *,
    registry_context: RegistryContext | None = None,
    technical_validated: bool = False,
    hardware_scope: HardwareScope | None = None,
) -> ScopeEvaluation:
    """Call from a future API/chat adapter after intake and specialist validation."""
    package = (
        provider
        if isinstance(provider, KnowledgePackage) or provider is None
        else provider.get(intake.domain, intake.jurisdiction)
    )
    coverage = resolve_pattern_coverage(intake, package, registry_context)
    proposal = discover(intake, package)
    if coverage.status != "cataloged":
        proposal = replace(proposal, status="pending_specialist", commercial_ready=False)
    return ScopeEvaluation(
        proposal,
        to_review_payload(
            proposal,
            evidence_reader,
            coverage=coverage,
            technical_validated=technical_validated,
            hardware_scope=hardware_scope,
        ),
    )
