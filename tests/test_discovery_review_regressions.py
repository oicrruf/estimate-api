"""Independent review regressions for the AT-240 domain engine."""

import json
from dataclasses import replace
from typing import Literal

import pytest

from estimate_api.discovery.engine import diff_proposals, discover, review
from estimate_api.discovery.models import KnowledgePackage, Need, ProjectIntake, ReviewAction, Rule
from estimate_api.discovery.service import evaluate_scope


def scope(*rules: Rule) -> tuple[ProjectIntake, KnowledgePackage]:
    return (
        ProjectIntake(
            "synthetic-project", "synthetic", "SYN", "synthetic", (Need("root", 2, "each"),)
        ),
        KnowledgePackage("synthetic", "v1", "SYN", "synthetic://review", rules),
    )


def rule(identifier: str, source: str, target: str, *, required: bool = True) -> Rule:
    return Rule(
        identifier,
        source,
        target,
        "material",
        "synthetic",
        "REQUIRES",
        "synthetic://evidence",
        required=required,
        quantity_mode="same",
    )


def test_parent_change_invalidates_transitive_quantities_and_approvals() -> None:
    intake, package = scope(
        rule("a", "root", "parent"), rule("b", "parent", "child"), rule("c", "child", "grandchild")
    )
    proposed = discover(intake, package)
    approved = review(
        proposed, tuple(ReviewAction(key, "approve") for key in ("parent", "child", "grandchild"))
    )
    assert approved.status == "approved"

    changed = review(approved, (ReviewAction("parent", "modify", 3, "each"),))
    lines = {line.key: line for line in changed.lines}
    assert lines["parent"].quantity == 3
    assert all(
        lines[key].quantity is None and lines[key].state == "pending_measurement"
        for key in ("child", "grandchild")
    )
    assert changed.status == "proposed" and not changed.commercial_ready
    with pytest.raises(ValueError, match="Review descendants"):
        review(
            approved,
            (ReviewAction("parent", "modify", 3, "each"), ReviewAction("child", "approve")),
        )


def test_shared_quantity_confirmation_keeps_other_blocks_and_stale_review() -> None:
    intake, package = scope(
        rule("a", "root", "shared"),
        rule("b", "root", "other"),
        rule("c", "other", "shared"),
        Rule(
            "d",
            "root",
            "conditional",
            "material",
            "synthetic",
            "REQUIRES",
            "synthetic://evidence",
            when_fact="site_fact",
            when_value=True,
        ),
    )
    proposed = discover(intake, package)
    assert set(proposed.blocking_facts) == {"quantity:shared", "site_fact"}
    confirmed = review(proposed, (ReviewAction("shared", "modify", 4, "each"),))
    assert confirmed.blocking_facts == ("site_fact",)
    assert confirmed.status != "approved" and not confirmed.commercial_ready
    rediscovered = diff_proposals(confirmed, discover(intake, package))
    assert "quantity:shared" in rediscovered.blocking_facts
    assert rediscovered.status != "approved" and not rediscovered.commercial_ready


def test_shared_quantity_approval_does_not_survive_rediscovery() -> None:
    intake, package = scope(
        rule("a", "root", "shared"),
        rule("b", "root", "other"),
        rule("c", "other", "shared"),
    )
    proposed = discover(intake, package)
    confirmed = review(proposed, (ReviewAction("shared", "modify", 4, "each"),))
    assert not confirmed.blocking_facts
    assert not any("cantidad total de shared" in question for question in confirmed.questions)
    approved = review(
        confirmed,
        (ReviewAction("shared", "approve"), ReviewAction("other", "approve")),
    )
    assert approved.status == "approved"
    changed = diff_proposals(approved, discover(intake, package))
    assert changed.status == "proposed" and not changed.commercial_ready
    assert "quantity:shared" in changed.blocking_facts
    assert next(line for line in changed.lines if line.key == "shared").state == "agent_proposed"


def test_unit_only_change_is_diffed_and_descendants_become_pending() -> None:
    intake, package = scope(rule("a", "root", "parent"), rule("b", "parent", "child"))
    proposed = discover(intake, package)
    changed = review(proposed, (ReviewAction("parent", "modify", 2, "packs"),))
    child = next(line for line in changed.lines if line.key == "child")
    assert child.quantity is None and child.state == "pending_measurement"
    assert ("parent", "changed") in diff_proposals(changed, proposed).changes
    unit_changed = replace(
        proposed,
        lines=tuple(
            replace(line, unit="packs") if line.key == "parent" else line for line in proposed.lines
        ),
    )
    assert ("parent", "changed") in diff_proposals(proposed, unit_changed).changes


def test_duplicate_optional_first_preserves_required_target() -> None:
    intake, package = scope(
        rule("a-optional", "root", "target", required=False), rule("z-required", "root", "target")
    )
    result = discover(intake, package)
    target = next(line for line in result.lines if line.key == "target")
    assert target.required
    assert result.evidence_paths.count(("root", "REQUIRES", "target")) == 2
    rejected = review(result, (ReviewAction("target", "reject"),))
    assert rejected.status == "blocked" and not rejected.commercial_ready


def test_cross_branch_cycle_is_rejected_before_review() -> None:
    intake, package = scope(
        rule("a", "root", "b"),
        rule("b", "root", "c"),
        rule("c", "b", "c"),
        rule("d", "c", "b"),
    )
    with pytest.raises(ValueError, match="Pattern cycle"):
        discover(intake, package)


@pytest.mark.parametrize("quantity", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_intake_and_review_quantity_are_rejected(quantity: float) -> None:
    intake, package = scope(rule("a", "root", "child"))
    invalid = replace(intake, needs=(Need("root", quantity, "each"),))
    with pytest.raises(ValueError, match="positive or pending quantities"):
        discover(invalid, package)
    with pytest.raises(ValueError, match="positive or pending quantities"):
        evaluate_scope(invalid, None)
    proposal = discover(intake, package)
    with pytest.raises(ValueError, match="positive quantity"):
        review(proposal, (ReviewAction("child", "modify", quantity, "each"),))
    assert json.dumps({"quantity": proposal.lines[1].quantity}, allow_nan=False)


@pytest.mark.parametrize(
    "mode,factor,parent",
    [
        ("fixed", float("nan"), 2),
        ("fixed", float("inf"), 2),
        ("multiply", float("inf"), 2),
        ("multiply", 1e308, 1e308),
    ],
)
def test_nonfinite_or_overflowed_derived_quantity_is_rejected(
    mode: Literal["fixed", "multiply"], factor: float, parent: float
) -> None:
    intake, package = scope(replace(rule("a", "root", "child"), quantity_mode=mode, factor=factor))
    intake = replace(intake, needs=(Need("root", parent, "each"),))
    with pytest.raises(ValueError, match="Invalid derived quantity"):
        discover(intake, package)
