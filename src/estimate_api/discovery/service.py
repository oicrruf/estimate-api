"""Deterministic backend entry point and versioned review payload for A2UI consumers."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal, Protocol, TypedDict

from estimate_api.contracts.universal_v1 import ProjectDocument
from estimate_api.knowledge.registry_v1 import CoverageResult

from .constraint_adapter import ConstraintScope, assess_constraints, attach_constraints
from .engine import discover
from .ethernet_adapter import TopologyScope, attach_topology_links
from .evidence import EvidenceReference, PatternRuleReference, TopologyLinkReference
from .hardware_adapter import HardwareScope
from .models import KnowledgePackage, PatternProvider, ProjectIntake, Proposal
from .pattern_adapter import PatternPlan, build_pattern_plan
from .registry_adapter import RegistryContext, resolve_pattern_coverage
from .trusted import is_reviewed_pattern, resolve_reviewed_package

SCHEMA_VERSION: Literal["scope-review.v1"] = "scope-review.v1"


class EvidenceReader(Protocol):
    def resolve(self, evidence_ids: tuple[str, ...]) -> tuple[EvidenceReference, ...]: ...

    def resolve_pattern_rules(
        self, pattern_id: str, rule_ids: tuple[str, ...]
    ) -> tuple[PatternRuleReference, ...]: ...

    def resolve_topology_links(
        self, link_ids: tuple[str, ...], dataset_id: str
    ) -> tuple[TopologyLinkReference, ...]: ...


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
    ruleIds: list[str]
    sourceRefs: list[str]
    candidatePaths: list[list[str]]
    patternId: str | None
    graphRulePaths: list[dict[str, str | None]]


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
    ethernet: EthernetPayload | None
    technicalBlockers: list[str]
    constraints: ConstraintPayload | None


class ConstraintPayload(TypedDict):
    status: str
    requiredCheckIds: list[str]
    missingCheckIds: list[str]
    reason: str | None
    findings: list[dict[str, object]]


class EthernetPayload(TypedDict):
    status: str
    links: list[dict[str, str | list[str] | None]]
    materials: list[dict[str, str | int | list[str] | None]]
    pending: list[str]
    incompatible: list[str]
    professionalValidationRequired: bool
    graphLinkPaths: list[dict[str, str | None]]
    materialTotalsComplete: bool


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
    ethernet_scope: TopologyScope | None = None,
    ethernet_dataset_id: str | None = None,
    constraint_scope: ConstraintScope | None = None,
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
        rule_references = (
            evidence_reader.resolve_pattern_rules(line.pattern_id, line.rule_ids)
            if evidence_reader is not None and line.pattern_id is not None and line.rule_ids
            else ()
        )
        status: Literal["capability_context", "unknown"] = (
            "capability_context"
            if references and all(ref.status == "capability_context" for ref in references)
            else "unknown"
        )
        if line.rule_id is not None and status == "unknown":
            evidence_complete = False
        if line.pattern_id is not None and (
            not rule_references or any(ref.status != "rule_context" for ref in rule_references)
        ):
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
                ruleIds=list(line.rule_ids),
                sourceRefs=list(line.source_refs),
                candidatePaths=[list(path) for path in line.candidate_paths],
                patternId=line.pattern_id,
                graphRulePaths=[
                    {
                        "patternId": ref.pattern_id,
                        "ruleId": ref.rule_id,
                        "sourceRef": ref.source_ref,
                        "status": ref.status,
                    }
                    for ref in rule_references
                ],
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
    ethernet_payload: EthernetPayload | None = None
    if ethernet_scope is not None:
        graph_links = (
            evidence_reader.resolve_topology_links(
                tuple(link.id for link in ethernet_scope.links), ethernet_dataset_id
            )
            if evidence_reader is not None and ethernet_dataset_id is not None
            else ()
        )
        ethernet_payload = EthernetPayload(
            status=ethernet_scope.status,
            links=[
                {
                    "id": link.id,
                    "status": link.status,
                    "reason": link.reason,
                    "requiredLengthM": link.required_length_m,
                    "evidenceIds": list(link.evidence_ids),
                }
                for link in ethernet_scope.links
            ],
            materials=[
                {
                    "cableId": item.cable_id,
                    "requiredLengthM": item.required_length_m,
                    "commercialRolls": item.commercial_rolls,
                    "ruleId": item.rule_id,
                    "evidenceIds": list(item.evidence_ids),
                }
                for item in ethernet_scope.materials
            ],
            pending=list(ethernet_scope.pending),
            incompatible=list(ethernet_scope.incompatible),
            professionalValidationRequired=ethernet_scope.professional_validation_required,
            materialTotalsComplete=ethernet_scope.material_totals_complete,
            graphLinkPaths=[
                {
                    "linkId": ref.link_id,
                    "endpointId": ref.endpoint_id,
                    "evidenceId": ref.evidence_id,
                    "status": ref.status,
                }
                for ref in graph_links
            ],
        )
    ethernet_ready = ethernet_scope is None or (
        ethernet_scope.status == "DERIVED" and not ethernet_scope.professional_validation_required
    )
    constraints_payload: ConstraintPayload | None = None
    if constraint_scope is not None:
        constraints_payload = ConstraintPayload(
            status=constraint_scope.status,
            requiredCheckIds=list(constraint_scope.required_check_ids),
            missingCheckIds=list(constraint_scope.missing_check_ids),
            reason=constraint_scope.reason,
            findings=[
                {
                    "checkId": item.check_id,
                    "kind": item.kind,
                    "status": item.status,
                    "blocking": item.blocking,
                    "reason": item.reason,
                    "subjectId": item.subject_id,
                    "packageId": item.package_id,
                    "sources": [
                        {
                            "entityId": ref.entity_id,
                            "revision": ref.revision,
                            "evidenceIds": list(ref.evidence_ids),
                        }
                        for ref in item.sources
                    ],
                }
                for item in constraint_scope.findings
            ],
        )
    constraint_ready = not proposal.constraint_check_ids or (
        constraint_scope is not None
        and constraint_scope.status == "pass"
        and set(proposal.constraint_check_ids)
        <= {item.check_id for item in constraint_scope.findings}
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
        and hardware_ready
        and ethernet_ready
        and constraint_ready,
        constraints=constraints_payload,
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
        ethernet=ethernet_payload,
        technicalBlockers=list(proposal.technical_blockers),
    )


def evaluate_scope(
    intake: ProjectIntake,
    provider: PatternProvider | KnowledgePackage | None,
    evidence_reader: EvidenceReader | None = None,
    *,
    registry_context: RegistryContext | None = None,
    technical_validated: bool = False,
    hardware_scope: HardwareScope | None = None,
    ethernet_scope: TopologyScope | None = None,
    ethernet_dataset_id: str | None = None,
    constraint_document: ProjectDocument | None = None,
    required_constraint_ids: tuple[str, ...] = (),
    _pattern_plan: PatternPlan | None = None,
) -> ScopeEvaluation:
    """Call from a future API/chat adapter after intake and specialist validation."""
    package = (
        provider
        if isinstance(provider, KnowledgePackage) or provider is None
        else provider.get(intake.domain, intake.jurisdiction)
    )
    coverage = resolve_pattern_coverage(intake, package, registry_context)
    if _pattern_plan is not None:
        if (
            package != _pattern_plan.package
            or not _pattern_plan.bindings
            or any(
                binding.pattern["sourceRef"] != _pattern_plan.package.source
                for binding in _pattern_plan.bindings
            )
            or any(not is_reviewed_pattern(binding.pattern) for binding in _pattern_plan.bindings)
            or build_pattern_plan(
                intake,
                _pattern_plan.bindings,
                registry_package_id=_pattern_plan.package.registry_package_id or "",
                source=_pattern_plan.package.source,
            )
            != _pattern_plan
        ):
            raise ValueError("Pattern plan differs from reviewed source expansion")
        trusted: KnowledgePackage | None = package
        trust_reason = None
    else:
        trusted, trust_reason = resolve_reviewed_package(intake, package, registry_context)
    if trust_reason is not None:
        coverage = CoverageResult(
            "pending_specialist",
            coverage.package_ids,
            coverage.conflicts,
            tuple(dict.fromkeys((*coverage.reasons, trust_reason))),
        )
    if (
        _pattern_plan is not None
        and registry_context is not None
        and coverage.status != "cataloged"
    ):
        trusted = None
    proposal = discover(intake, trusted)
    if coverage.status != "cataloged":
        proposal = replace(proposal, status="pending_specialist", commercial_ready=False)
    if ethernet_scope is not None:
        proposal = attach_topology_links(proposal, ethernet_scope)
    constraint_scope = assess_constraints(
        constraint_document, required_constraint_ids, intake.project_id
    )
    proposal = attach_constraints(proposal, constraint_scope)
    return ScopeEvaluation(
        proposal,
        to_review_payload(
            proposal,
            evidence_reader,
            coverage=coverage,
            technical_validated=technical_validated,
            hardware_scope=hardware_scope,
            ethernet_scope=ethernet_scope,
            ethernet_dataset_id=ethernet_dataset_id,
            constraint_scope=constraint_scope,
        ),
    )


def evaluate_pattern_scope(
    intake: ProjectIntake,
    plan: PatternPlan,
    evidence_reader: EvidenceReader | None = None,
    *,
    registry_context: RegistryContext | None = None,
    previous: Proposal | None = None,
    ethernet_scope: TopologyScope | None = None,
    ethernet_dataset_id: str | None = None,
    constraint_document: ProjectDocument | None = None,
    required_constraint_ids: tuple[str, ...] = (),
) -> ScopeEvaluation:
    """Evaluate actual AT-247 candidates; always retain pending and stale-review state."""
    from .engine import diff_proposals

    if (
        previous is not None
        and ethernet_scope is None
        and any(line.work_package == "ethernet" for line in previous.lines)
    ):
        raise ValueError("Topology is required when revalidating prior Ethernet scope")
    if previous is not None:
        required_constraint_ids = tuple(
            dict.fromkeys((*required_constraint_ids, *previous.constraint_check_ids))
        )
    evaluated = evaluate_scope(
        intake,
        plan.package,
        evidence_reader,
        registry_context=registry_context,
        ethernet_scope=ethernet_scope,
        ethernet_dataset_id=ethernet_dataset_id,
        constraint_document=constraint_document,
        required_constraint_ids=required_constraint_ids,
        _pattern_plan=plan,
    )
    proposal = evaluated.proposal
    pending = tuple(dict.fromkeys((*proposal.blocking_facts, *plan.pending)))
    if pending or plan.limit_reached:
        questions = tuple(
            dict.fromkeys(
                (*proposal.questions, *(f"Confirmar patrón: {item}" for item in plan.pending))
            )
        )
        proposal = replace(
            proposal,
            blocking_facts=pending,
            questions=questions,
            status="pending_specialist"
            if plan.limit_reached or proposal.status == "pending_specialist"
            else "proposed",
            commercial_ready=False,
        )
    if previous is not None:
        proposal = diff_proposals(previous, proposal)
    coverage = resolve_pattern_coverage(intake, plan.package, registry_context)
    constraint_scope = assess_constraints(
        constraint_document, required_constraint_ids, intake.project_id
    )
    return ScopeEvaluation(
        proposal,
        to_review_payload(
            proposal,
            evidence_reader,
            coverage=coverage,
            ethernet_scope=ethernet_scope,
            ethernet_dataset_id=ethernet_dataset_id,
            constraint_scope=constraint_scope,
        ),
    )
