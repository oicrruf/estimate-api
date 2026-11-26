"""AT-266 regressions for rule provenance and specialist revalidation."""

import copy
import json
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

from estimate_api.discovery.engine import discover, revalidate
from estimate_api.discovery.models import KnowledgePackage, Need, ProjectIntake, Rule
from estimate_api.discovery.pattern_adapter import PatternBinding, build_pattern_plan
from estimate_api.discovery.registry_adapter import RegistryContext
from estimate_api.discovery.service import evaluate_pattern_scope, evaluate_scope
from estimate_api.patterns.v1 import Fact

ROOT = Path(__file__).resolve().parents[1]


def case(domain: str) -> tuple[ProjectIntake, KnowledgePackage, RegistryContext]:
    name, root, category = {
        "camera": ("cameras", "camera", "fictional-camera"),
        "painting": ("painting", "paint_surface", "fictional-paint"),
        "event": ("event", "event_task", "fictional-event"),
    }[domain]
    project = json.loads((ROOT / f"fixtures/valid/{name}.json").read_text())
    registry = json.loads((ROOT / "fixtures/knowledge/registry-synthetic.json").read_text())
    item = registry["packages"][0]
    item["id"] = f"catalog:{domain}"
    item["namespace"] = f"example.{domain}"
    item["applicability"]["categories"] = [category]
    item["applicability"]["scopes"] = [{"kind": "project", "id": f"{domain}:project"}]
    item["categorySpecs"][0]["category"] = category
    item["installationPatterns"][0]["category"] = category
    item["review"].update(
        state="verified",
        reviewerRef="synthetic://reviewer",
        evidenceRefs=["synthetic://review"],
    )
    intake = ProjectIntake(
        project["projectId"],
        domain,
        "TEST-ZONE-A",
        "synthetic",
        (Need(root, 1, "each"),),
    )
    package = KnowledgePackage(
        domain,
        "1.0.0",
        "TEST-ZONE-A",
        "synthetic://unattested",
        (
            Rule(
                "unbound",
                root,
                "camera:mount",
                "material",
                "installation",
                "REQUIRES",
                "synthetic",
                quantity_mode="fixed",
                factor=1,
            ),
        ),
        registry_package_id=f"catalog:{domain}",
    )
    return (
        intake,
        package,
        RegistryContext(
            project, registry, category, {"kind": "project", "id": f"{domain}:project"}
        ),
    )


@pytest.mark.parametrize("domain", ["camera", "painting", "event"])
def test_unattested_rule_cannot_inject_cross_domain_line(domain: str) -> None:
    intake, package, context = case(domain)
    result = evaluate_scope(intake, package, registry_context=context)
    assert result.payload["coverage"]["status"] == "pending_specialist"
    assert result.payload["coverage"]["reasons"] == ["reviewed_package_missing"]
    assert {line.key for line in result.proposal.lines} == {intake.needs[0].key}
    assert not result.payload["commercialReady"]


@pytest.mark.parametrize("domain", ["camera", "painting", "event"])
def test_standalone_revalidate_cannot_promote_specialist_scope(domain: str) -> None:
    intake, package, _ = case(domain)
    prior = discover(intake, None)
    updated = revalidate(prior, intake, package)
    assert updated.status == "pending_specialist"
    assert not updated.commercial_ready
    assert "Specialist coverage requires verification" in updated.questions


def test_mutated_attested_plan_is_rejected_before_discovery() -> None:
    intake, _, _ = case("camera")
    patterns = json.loads((ROOT / "fixtures/patterns/patterns.v1.json").read_text())["patterns"]
    pattern = next(item for item in patterns if item["id"].endswith("poe-camera"))
    facts = {
        "application": {"state": "confirmed", "value": True, "evidenceId": "EV-APP"},
        "wired_run": {"state": "confirmed", "value": True, "evidenceId": "EV-WIRED"},
        "mount_required": {"state": "confirmed", "value": False, "evidenceId": "EV-MOUNT"},
        "poe_source": {"state": "confirmed", "value": True, "evidenceId": "EV-POE"},
        "utp_ends": {"state": "confirmed", "value": 2, "evidenceId": "EV-ENDS"},
    }
    plan = build_pattern_plan(
        intake,
        (PatternBinding("camera", pattern, cast(dict[str, Fact], facts)),),
        registry_package_id="catalog:camera",
        source=pattern["sourceRef"],
    )
    injected = replace(
        plan,
        package=replace(
            plan.package,
            rules=plan.package.rules
            + (
                Rule(
                    "forged",
                    "camera",
                    "paint:extra",
                    "material",
                    "installation",
                    "REQUIRES",
                    "synthetic",
                    quantity_mode="fixed",
                    factor=1,
                ),
            ),
        ),
    )
    with pytest.raises(ValueError, match="differs"):
        evaluate_pattern_scope(intake, injected)
    spoofed_source = replace(plan, package=replace(plan.package, source="synthetic://spoof"))
    with pytest.raises(ValueError, match="reviewed source"):
        evaluate_pattern_scope(intake, spoofed_source)
    changed_pattern = copy.deepcopy(pattern)
    changed_pattern["sourceRef"] = "synthetic://unreviewed-change"
    altered_plan = build_pattern_plan(
        intake,
        (PatternBinding("camera", changed_pattern, cast(dict[str, Fact], facts)),),
        registry_package_id="catalog:camera",
        source=pattern["sourceRef"],
    )
    with pytest.raises(ValueError, match="reviewed source"):
        evaluate_pattern_scope(intake, altered_plan)
