"""Fail-closed bridge from AT-267 project checks to scope review."""

from __future__ import annotations

from dataclasses import dataclass, replace

from estimate_api.constraints import Finding, evaluate_global_constraints
from estimate_api.contracts.universal_v1 import ProjectDocument

from .models import Proposal


@dataclass(frozen=True)
class ConstraintScope:
    status: str
    findings: tuple[Finding, ...]
    required_check_ids: tuple[str, ...]
    missing_check_ids: tuple[str, ...]
    reason: str | None = None


def assess_constraints(
    document: ProjectDocument | None,
    required_check_ids: tuple[str, ...],
    project_id: str | None = None,
) -> ConstraintScope | None:
    """Require explicit applicable checks; never treat an omitted check as a pass."""
    if document is None and not required_check_ids:
        return None
    if len(required_check_ids) != len(set(required_check_ids)):
        raise ValueError("Duplicate required constraint check")
    if document is None:
        return ConstraintScope(
            "pending", (), required_check_ids, required_check_ids, "document_missing"
        )
    if project_id is not None and document.get("projectId") != project_id:
        return ConstraintScope(
            "pending", (), required_check_ids, required_check_ids, "project_mismatch"
        )
    try:
        findings = evaluate_global_constraints(document)
    except ValueError as exc:
        return ConstraintScope("pending", (), required_check_ids, required_check_ids, str(exc))
    found = {finding.check_id for finding in findings}
    missing = tuple(check_id for check_id in required_check_ids if check_id not in found)
    if len(found) != len(findings):
        return ConstraintScope(
            "pending", findings, required_check_ids, missing, "duplicate_check_id"
        )
    if not findings:
        return ConstraintScope("pending", (), required_check_ids, missing, "no_constraint_checks")
    status = (
        "pending"
        if missing or any(item.status == "pending" for item in findings)
        else "fail"
        if any(item.status == "fail" for item in findings)
        else "pass"
    )
    return ConstraintScope(status, findings, required_check_ids, missing)


def attach_constraints(proposal: Proposal, scope: ConstraintScope | None) -> Proposal:
    if scope is None:
        return proposal
    blockers = tuple(
        dict.fromkeys(
            (
                *proposal.technical_blockers,
                *(
                    f"constraint:{item.check_id}:{item.status}"
                    for item in scope.findings
                    if item.blocking
                ),
                *(f"constraint:{item}:missing" for item in scope.missing_check_ids),
                *((f"constraint:{scope.reason}",) if scope.reason else ()),
            )
        )
    )
    if scope.status != "pass" and not blockers:
        blockers = ("constraint:pending",)
    return replace(
        proposal,
        status="blocked"
        if blockers and proposal.status != "pending_specialist"
        else proposal.status,
        technical_blockers=blockers,
        constraint_check_ids=tuple(
            dict.fromkeys((*scope.required_check_ids, *(item.check_id for item in scope.findings)))
        ),
        commercial_ready=proposal.commercial_ready and not blockers,
    )
