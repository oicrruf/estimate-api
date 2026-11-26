"""Synthetic, in-memory AT-246 intake to AT-240 scope-review boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from estimate_api.contracts.universal_v1 import ProjectDocument
from estimate_api.discovery.constraint_adapter import assess_constraints
from estimate_api.discovery.engine import diff_proposals
from estimate_api.discovery.models import Need, ProjectIntake, Proposal
from estimate_api.discovery.service import (
    ScopeEvaluation,
    evaluate_scope,
    to_review_payload,
)
from estimate_api.discovery.trusted import reviewed_package
from estimate_api.domain.scope_capture import (
    Certainty,
    Fact,
    ScopeDraft,
    ScopeIntake,
    build_scope_draft,
)

PROJECT_ID = "camera:goal"
REQUIRED_CHECKS = ("global:total-ports", "global:poe-ports")


@dataclass(frozen=True)
class NetworkIntake:
    """Explicit synthetic counts; never parse or infer them from description text."""

    scope: ScopeIntake
    cameras: Fact[int] | None
    uplink_ports: Fact[int] | None


@dataclass(frozen=True)
class ConstraintSnapshot:
    """Caller-attested input binding; AT-248 must verify real evidence freshness."""

    document: ProjectDocument
    cameras: int
    uplink_ports: int


@dataclass(frozen=True)
class IntakeReview:
    stage: Literal["scope_review_pending"]
    review_required: Literal[True]
    persisted: Literal[False]
    scope_draft: ScopeDraft
    scope_review: ScopeEvaluation
    intake_questions: tuple[str, ...]


def _confirmed_count(value: Fact[int] | None) -> int | None:
    if value is None:
        return None
    if type(value.value) is not int or value.value <= 0:
        raise ValueError("Counts must be positive whole numbers")
    return value.value if value.certainty == Certainty.CONFIRMED else None


def preview_scope_review(
    intake: NetworkIntake,
    *,
    snapshot: ConstraintSnapshot | None = None,
    previous: Proposal | None = None,
) -> IntakeReview:
    """Produce review data without persistence, approval, or technical validation."""
    draft = build_scope_draft(intake.scope)
    cameras = _confirmed_count(intake.cameras)
    uplink_ports = _confirmed_count(intake.uplink_ports)
    if previous is not None and previous.project_id != PROJECT_ID:
        raise ValueError("Previous proposal belongs to another project")
    if snapshot is not None and (
        snapshot.cameras != cameras
        or snapshot.uplink_ports != uplink_ports
        or snapshot.document.get("projectId") != PROJECT_ID
    ):
        raise ValueError("Constraint evidence does not match confirmed intake")
    # A prior proposal makes every constraint check stale. A fresh AT-248 check
    # must be supplied in a separate review cycle; never recycle its document.
    document = snapshot.document if snapshot is not None and previous is None else None
    required_checks = tuple(
        dict.fromkeys((*REQUIRED_CHECKS, *(previous.constraint_check_ids if previous else ())))
    )
    project = ProjectIntake(
        PROJECT_ID,
        "synthetic_network",
        "TEST-ZONE-A",
        intake.scope.description,
        (Need("camera:camera", cameras, "each"), Need("network:uplink", uplink_ports, "port")),
    )
    evaluated = evaluate_scope(
        project,
        reviewed_package("catalog:camera-at266-v1"),
        constraint_document=document,
        required_constraint_ids=required_checks,
    )
    if previous is not None:
        fresh = diff_proposals(previous, evaluated.proposal)
        evaluated = ScopeEvaluation(
            fresh,
            to_review_payload(
                fresh,
                constraint_scope=assess_constraints(None, required_checks, PROJECT_ID),
            ),
        )
    questions: list[str] = []
    if cameras is None:
        questions.append("Confirm the PoE camera count with evidence.")
    if uplink_ports is None:
        questions.append("Confirm the separate uplink port count with evidence.")
    return IntakeReview("scope_review_pending", True, False, draft, evaluated, tuple(questions))
