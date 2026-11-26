"""AT-240 contract against integrated AT-247/239/265 synthetic inputs."""

import copy
import json
import tempfile
from dataclasses import replace
from pathlib import Path

import pytest
import relate
from jsonschema import Draft202012Validator

from estimate_api.discovery.engine import review
from estimate_api.discovery.ethernet_adapter import (
    TopologyLink,
    TopologyScope,
    attach_topology_links,
    evaluate_ethernet_scope,
)
from estimate_api.discovery.evidence import (
    EvidenceReference,
    PatternRuleReference,
    RelateEvidenceReader,
    TopologyLinkReference,
)
from estimate_api.discovery.models import Need, ProjectIntake, ReviewAction
from estimate_api.discovery.pattern_adapter import PatternBinding, PatternPlan, build_pattern_plan
from estimate_api.discovery.registry_adapter import RegistryContext
from estimate_api.discovery.service import evaluate_pattern_scope, evaluate_scope, to_review_payload
from estimate_api.patterns.relate_seed import seed_patterns
from estimate_api.patterns.v1 import Fact, Pattern, registry_reference

ROOT = Path(__file__).resolve().parents[1]
PATTERNS: list[Pattern] = json.loads(
    (ROOT / "fixtures/patterns/patterns.v1.json").read_text(encoding="utf-8")
)["patterns"]
BY_NAME = {item["id"].split(":")[-1]: item for item in PATTERNS}


def confirmed(value: str | bool | int, evidence: str) -> Fact:
    return {"state": "confirmed", "value": value, "evidenceId": evidence}


def registry_context(pattern: Pattern) -> RegistryContext:
    project = json.loads((ROOT / "fixtures/valid/cameras.json").read_text(encoding="utf-8"))
    registry = json.loads(
        (ROOT / "fixtures/knowledge/registry-synthetic.json").read_text(encoding="utf-8")
    )
    item = registry["packages"][0]
    item["applicability"]["categories"] = [pattern["category"]]
    item["categorySpecs"][0]["category"] = pattern["category"]
    item["installationPatterns"] = [registry_reference(pattern)]
    item["review"].update(
        state="verified",
        reviewerRef="synthetic://reviewer",
        evidenceRefs=["synthetic://review"],
    )
    return RegistryContext(
        project, registry, pattern["category"], {"kind": "project", "id": "camera:project"}
    )


def intake(key: str, quantity: int | None) -> ProjectIntake:
    return ProjectIntake(
        "camera:goal",
        "synthetic_network",
        "TEST-ZONE-A",
        "Synthetic installation",
        (Need(key, quantity, "each"),),
    )


def plan(project: ProjectIntake, binding: PatternBinding) -> PatternPlan:
    return build_pattern_plan(
        project,
        (binding,),
        registry_package_id="catalog:camera-v1",
        source="synthetic://at-247/patterns/1.0.0",
    )


def test_versioned_candidates_keep_provenance_and_revalidate_counts() -> None:
    pattern = BY_NAME["poe-camera"]
    project = intake("camera", 8)
    facts = {
        "application": confirmed(True, "EV-APPLICATION"),
        "wired_run": confirmed(True, "EV-WIRED"),
        "mount_required": confirmed(True, "EV-MOUNT"),
        "poe_source": confirmed(True, "EV-POE"),
        "utp_ends": confirmed(2, "EV-ENDS"),
    }
    binding = PatternBinding("camera", pattern, facts)
    context = registry_context(pattern)
    evaluated = evaluate_pattern_scope(project, plan(project, binding), registry_context=context)
    lines = {line.key: line for line in evaluated.proposal.lines}
    connector = lines["at247:item:utp-connector"]
    assert connector.quantity == 16
    assert connector.rule_id == f"{pattern['id']}/{connector.key}"
    assert connector.rule_ids == ("AT247-CAMERA_ENDS",)
    assert "EV-ENDS" in connector.evidence_ids
    assert connector.candidate_paths[0] == (
        "at247:item:poe-camera",
        "at247:item:utp",
        "at247:item:utp-connector",
    )
    assert evaluated.payload["coverage"]["status"] == "cataloged"
    assert not evaluated.payload["commercialReady"]
    blocked = review(evaluated.proposal, (ReviewAction(connector.key, "reject"),))
    assert blocked.status == "blocked" and not blocked.commercial_ready
    increased = replace(project, needs=(Need("camera", 12, "each"),))
    updated = evaluate_pattern_scope(
        increased, plan(increased, binding), registry_context=context, previous=blocked
    )
    assert (connector.key, "changed") in updated.proposal.changes
    assert next(line for line in updated.proposal.lines if line.key == connector.key).quantity == 24
    assert all(line.state != "user_approved" for line in updated.proposal.lines)
    assert {line.key for line in evaluated.proposal.lines if line.required} == {
        line.key for line in updated.proposal.lines if line.required
    }
    schema = json.loads(
        (ROOT / "src/estimate_api/discovery/schemas/scope-review.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator(schema).validate(json.loads(json.dumps(updated.payload)))


def test_reviewing_real_utp_candidate_invalidates_its_precomputed_descendants() -> None:
    pattern = BY_NAME["poe-camera"]
    project = intake("camera", 8)
    facts = {
        "application": confirmed(True, "EV-APPLICATION"),
        "wired_run": confirmed(True, "EV-WIRED"),
        "mount_required": confirmed(False, "EV-MOUNT"),
        "poe_source": confirmed(True, "EV-POE"),
        "utp_ends": confirmed(2, "EV-ENDS"),
    }
    evaluated = evaluate_pattern_scope(
        project,
        plan(project, PatternBinding("camera", pattern, facts)),
        registry_context=registry_context(pattern),
    )
    assert (
        "at247:item:utp",
        "REQUIRES",
        "at247:item:utp-connector",
    ) in evaluated.proposal.evidence_paths
    proposed = {line.key: line for line in evaluated.proposal.lines}
    assert proposed["at247:item:utp"].quantity == 8
    assert proposed["at247:item:utp-connector"].quantity == 16
    approved = review(
        evaluated.proposal,
        tuple(
            ReviewAction(line.key, "approve")
            for line in evaluated.proposal.lines
            if line.state == "agent_proposed"
        ),
    )
    assert approved.status == "approved" and approved.commercial_ready
    changed = review(approved, (ReviewAction("at247:item:utp", "modify", 12, "candidate"),))
    changed_lines = {line.key: line for line in changed.lines}
    for key in ("at247:item:utp-connector", "at247:item:link-test"):
        assert changed_lines[key].quantity is None
        assert changed_lines[key].state == "pending_measurement"
    assert changed_lines["at247:item:poe-power"].state == "user_approved"
    reapproved_utp = review(changed, (ReviewAction("at247:item:utp", "approve"),))
    assert reapproved_utp.status == "proposed" and not reapproved_utp.commercial_ready


def test_pending_pattern_facts_do_not_hide_technical_blockers() -> None:
    pattern = BY_NAME["poe-camera"]
    project = intake("camera", 2)
    facts = {
        "application": confirmed(True, "EV-APPLICATION"),
        "wired_run": confirmed(True, "EV-WIRED"),
        "mount_required": confirmed(False, "EV-MOUNT"),
        "poe_source": confirmed(True, "EV-POE"),
    }
    binding = PatternBinding("camera", pattern, facts)
    pattern_plan = plan(project, binding)
    context = registry_context(pattern)
    ordinary = evaluate_pattern_scope(project, pattern_plan, registry_context=context)
    assert ordinary.proposal.status == ordinary.payload["status"] == "proposed"
    assert "camera:utp_ends" in ordinary.proposal.blocking_facts
    missing_check = evaluate_pattern_scope(
        project,
        pattern_plan,
        registry_context=context,
        required_constraint_ids=("global:total-ports",),
    )
    assert missing_check.proposal.status == missing_check.payload["status"] == "blocked"
    assert "constraint:document_missing" in missing_check.proposal.technical_blockers
    incompatible = evaluate_pattern_scope(
        project,
        pattern_plan,
        registry_context=context,
        ethernet_scope=TopologyScope(
            "REVIEW_REQUIRED", (), (), (), ("incompatible-route",), True, False
        ),
    )
    assert incompatible.proposal.status == incompatible.payload["status"] == "blocked"
    assert "incompatible-route" in incompatible.proposal.technical_blockers
    assert not missing_check.payload["commercialReady"]
    assert not incompatible.payload["commercialReady"]
    still_blocked = attach_topology_links(
        missing_check.proposal, TopologyScope("PENDING", (), (), (), (), True, False)
    )
    assert still_blocked.status == "blocked"
    assert still_blocked.technical_blockers == missing_check.proposal.technical_blockers


def test_topology_additions_obey_discovery_line_limit() -> None:
    topology = TopologyScope(
        "PENDING",
        tuple(
            TopologyLink(f"LINK-{index:03}", "PENDING", "measurement", None, ())
            for index in range(100)
        ),
        (),
        (),
        (),
        True,
        False,
    )
    with pytest.raises(ValueError, match="Topology line limit"):
        evaluate_scope(intake("camera", 1), None, ethernet_scope=topology)


def test_many_shared_evidence_ids_are_batched_without_losing_provenance() -> None:
    pattern = BY_NAME["poe-camera"]
    project = replace(
        intake("camera-00", 1),
        needs=tuple(Need(f"camera-{index:02}", 1, "each") for index in range(68)),
    )
    bindings = tuple(
        PatternBinding(
            need.key,
            pattern,
            {
                "application": confirmed(True, f"EV-APP-{index:02}"),
                "wired_run": confirmed(True, f"EV-RUN-{index:02}"),
                "mount_required": confirmed(False, f"EV-MOUNT-{index:02}"),
                "poe_source": confirmed(True, f"EV-POE-{index:02}"),
                "utp_ends": confirmed(
                    2, "EV-ENDS-unavailable" if index == 33 else f"EV-ENDS-{index:02}"
                ),
            },
        )
        for index, need in enumerate(project.needs)
    )
    pattern_plan = build_pattern_plan(
        project,
        bindings,
        registry_package_id="catalog:camera-v1",
        source="synthetic://at-247/patterns/1.0.0",
    )

    class BoundedReader:
        def __init__(self) -> None:
            self.calls: list[tuple[str, ...]] = []

        def resolve(self, evidence_ids: tuple[str, ...]) -> tuple[EvidenceReference, ...]:
            assert 0 < len(evidence_ids) <= 100
            assert len(evidence_ids) == len(set(evidence_ids))
            self.calls.append(evidence_ids)
            return tuple(
                EvidenceReference(
                    identifier,
                    "unknown" if identifier.endswith("-unavailable") else "capability_context",
                    None,
                    () if identifier.endswith("-unavailable") else (("p", "c", identifier),),
                )
                for identifier in evidence_ids
            )

        def resolve_pattern_rules(
            self, pattern_id: str, rule_ids: tuple[str, ...]
        ) -> tuple[PatternRuleReference, ...]:
            return tuple(
                PatternRuleReference(pattern_id, rule_id, "synthetic://source", "rule_context")
                for rule_id in rule_ids
            )

        def resolve_topology_links(
            self, link_ids: tuple[str, ...], dataset_id: str
        ) -> tuple[TopologyLinkReference, ...]:
            return ()

    reader = BoundedReader()
    result = evaluate_pattern_scope(
        project, pattern_plan, reader, registry_context=registry_context(pattern)
    )
    connector = next(
        line for line in result.proposal.lines if line.key == "at247:item:utp-connector"
    )
    rendered = next(line for line in result.payload["lines"] if line["key"] == connector.key)
    assert len(result.proposal.lines) == 72
    assert len(connector.evidence_ids) == len(rendered["evidence"]) == 204
    assert [item["id"] for item in rendered["evidence"]] == list(connector.evidence_ids)
    assert len(rendered["ruleProvenance"]) == 68
    assert any(len(call) == 100 for call in reader.calls)
    assert any(len(call) == 4 for call in reader.calls)
    assert rendered["evidenceStatus"] == "unknown"
    assert not result.payload["commercialReady"]

    with tempfile.TemporaryDirectory(prefix="at240-many-evidence-") as directory:
        connection = relate.connect(str(Path(directory) / "patterns.db"))
        seed_patterns(connection, [pattern])
        real_reader = RelateEvidenceReader(connection, "estimate-hackathon-v1")
        real_result = evaluate_pattern_scope(
            project, pattern_plan, real_reader, registry_context=registry_context(pattern)
        )
        real_line = next(
            line for line in real_result.payload["lines"] if line["key"] == connector.key
        )
        assert len(real_line["evidence"]) == 204
        assert real_line["evidenceStatus"] == "unknown"
        connection.close()

    class TruncatedReader(BoundedReader):
        def resolve(self, evidence_ids: tuple[str, ...]) -> tuple[EvidenceReference, ...]:
            return super().resolve(evidence_ids[:-1])

    with pytest.raises(ValueError, match="incomplete or reordered"):
        to_review_payload(result.proposal, TruncatedReader())

    empty_reader = BoundedReader()
    to_review_payload(evaluate_scope(intake("uncovered", None), None).proposal, empty_reader)
    assert empty_reader.calls == []


def test_reused_pattern_bindings_keep_distinct_rule_ids_and_shared_quantity_block() -> None:
    pattern = BY_NAME["poe-camera"]
    project = replace(
        intake("camera-zone-a", 2),
        needs=(Need("camera-zone-a", 2, "each"), Need("camera-zone-b", 3, "each")),
    )
    facts = {
        "application": confirmed(True, "EV-APPLICATION"),
        "wired_run": confirmed(True, "EV-WIRED"),
        "mount_required": confirmed(False, "EV-MOUNT"),
        "poe_source": confirmed(True, "EV-POE"),
        "utp_ends": confirmed(2, "EV-ENDS"),
    }
    facts_b: dict[str, Fact] = {
        key: {
            "state": fact["state"],
            "value": fact["value"],
            "evidenceId": f"{fact['evidenceId']}-B",
        }
        for key, fact in facts.items()
    }
    bindings = (
        PatternBinding("camera-zone-a", pattern, facts),
        PatternBinding("camera-zone-b", pattern, facts_b),
    )
    pattern_plan = build_pattern_plan(
        project,
        bindings,
        registry_package_id="catalog:camera-v1",
        source="synthetic://at-247/patterns/1.0.0",
    )
    ids = [rule.id for rule in pattern_plan.package.rules]
    assert len(ids) == len(set(ids))
    assert {json.loads(identifier)[0] for identifier in ids} == {"camera-zone-a", "camera-zone-b"}
    result = evaluate_pattern_scope(
        project, pattern_plan, registry_context=registry_context(pattern)
    )
    assert {line.key for line in result.proposal.lines} >= {
        "camera-zone-a",
        "camera-zone-b",
        "at247:item:utp-connector",
    }
    assert "quantity:at247:item:utp-connector" in result.proposal.blocking_facts
    assert not result.payload["commercialReady"]
    connector = next(
        line for line in result.proposal.lines if line.key == "at247:item:utp-connector"
    )
    assert {origin.parent_key for origin in connector.rule_provenance} == {
        "camera-zone-a",
        "camera-zone-b",
    }
    assert {origin.rule_id for origin in connector.rule_provenance} == {
        rule.id for rule in pattern_plan.package.rules if rule.target_key == connector.key
    }
    assert all(
        origin.rule_ids and origin.source_refs and origin.candidate_paths
        for origin in connector.rule_provenance
    )
    assert "EV-ENDS" in connector.evidence_ids and "EV-ENDS-B" in connector.evidence_ids
    assert "EV-ENDS" in connector.rule_provenance[0].evidence_ids
    assert "EV-ENDS-B" in connector.rule_provenance[1].evidence_ids

    class MissingSecondEvidence:
        def resolve(self, evidence_ids: tuple[str, ...]) -> tuple[EvidenceReference, ...]:
            return tuple(
                EvidenceReference(
                    identifier,
                    "unknown" if identifier.endswith("-B") else "capability_context",
                    None,
                    () if identifier.endswith("-B") else (("product", "capability", identifier),),
                )
                for identifier in evidence_ids
            )

        def resolve_pattern_rules(
            self, pattern_id: str, rule_ids: tuple[str, ...]
        ) -> tuple[PatternRuleReference, ...]:
            return tuple(
                PatternRuleReference(pattern_id, rule_id, "synthetic://source", "rule_context")
                for rule_id in rule_ids
            )

        def resolve_topology_links(
            self, link_ids: tuple[str, ...], dataset_id: str
        ) -> tuple[TopologyLinkReference, ...]:
            return ()

    reader = MissingSecondEvidence()
    before = to_review_payload(result.proposal, reader)
    rendered = next(line for line in before["lines"] if line["key"] == connector.key)
    assert rendered["evidenceStatus"] == "unknown"
    assert {origin["parentKey"] for origin in rendered["ruleProvenance"]} == {
        "camera-zone-a",
        "camera-zone-b",
    }
    confirmed_scope = review(
        result.proposal, (ReviewAction(connector.key, "modify", 10, connector.unit),)
    )
    assert "quantity:at247:item:utp-connector" not in confirmed_scope.blocking_facts
    assert "quantity:at247:item:link-test" in confirmed_scope.blocking_facts
    after = to_review_payload(confirmed_scope, reader)
    confirmed_line = next(line for line in after["lines"] if line["key"] == connector.key)
    assert confirmed_line["evidenceStatus"] == "unknown"
    assert confirmed_line["ruleProvenance"] == rendered["ruleProvenance"]
    assert not after["commercialReady"]
    schema = json.loads(
        (ROOT / "src/estimate_api/discovery/schemas/scope-review.v1.schema.json").read_text()
    )
    validator = Draft202012Validator(schema)
    validator.validate(json.loads(json.dumps(before, allow_nan=False)))
    validator.validate(json.loads(json.dumps(after, allow_nan=False)))


def test_confirmed_alternative_changes_scope_but_unknown_does_not() -> None:
    pattern = BY_NAME["mesh"]
    project = intake("mesh", 1)
    facts = {
        "application": confirmed(True, "EV-APPLICATION"),
        "backhaul": confirmed("wired", "EV-WIRED"),
        "mount_required": confirmed(False, "EV-MOUNT"),
        "power_required": confirmed(False, "EV-POWER"),
        "utp_ends": confirmed(2, "EV-ENDS"),
    }
    context = registry_context(pattern)
    wired = evaluate_pattern_scope(
        project,
        plan(project, PatternBinding("mesh", pattern, facts)),
        registry_context=context,
    )
    rejected = review(wired.proposal, (ReviewAction("at247:item:utp", "reject"),))
    assert rejected.status == "blocked"
    unknown_facts = copy.deepcopy(facts)
    unknown_facts["backhaul"] = {"state": "unknown", "value": None, "evidenceId": None}
    unknown = evaluate_pattern_scope(
        project,
        plan(project, PatternBinding("mesh", pattern, unknown_facts)),
        registry_context=context,
        previous=rejected,
    )
    assert unknown.proposal.status == "pending_specialist"
    assert "at247:item:wireless-survey" not in {line.key for line in unknown.proposal.lines}
    wireless_facts = copy.deepcopy(facts)
    wireless_facts["backhaul"] = confirmed("wireless", "EV-WIRELESS")
    wireless = evaluate_pattern_scope(
        project,
        plan(project, PatternBinding("mesh", pattern, wireless_facts)),
        registry_context=context,
        previous=rejected,
    )
    keys = {line.key for line in wireless.proposal.lines}
    assert "at247:item:wireless-survey" in keys
    assert "at247:item:utp" not in keys
    assert ("at247:item:utp", "removed") in wireless.proposal.changes
    assert ("at247:item:wireless-survey", "added") in wireless.proposal.changes
    assert not wireless.payload["commercialReady"]


def test_topology_preserves_all_required_links_and_unknown_lengths() -> None:
    fixture = json.loads((ROOT / "demo/ethernet/fixture.json").read_text(encoding="utf-8"))
    topology = evaluate_ethernet_scope(fixture["catalog"], fixture["topology"])
    assert topology.status == "PENDING"
    assert {item.id for item in topology.links} == {
        "LINK-CAM-1",
        "LINK-CAM-2",
        "LINK-MESH-2",
        "LINK-UPLINK",
    }
    assert next(item for item in topology.links if item.id == "LINK-CAM-1").required_length_m
    assert (
        next(item for item in topology.links if item.id == "LINK-CAM-2").required_length_m is None
    )
    assert topology.materials and topology.materials[0].evidence_ids
    assert not topology.material_totals_complete
    assert topology.materials[0].commercial_rolls is None
    pattern = BY_NAME["poe-camera"]
    project = intake("camera", 8)
    facts = {
        "application": confirmed(True, "EV-APPLICATION"),
        "wired_run": confirmed(True, "EV-WIRED"),
        "mount_required": confirmed(False, "EV-MOUNT"),
        "poe_source": confirmed(True, "EV-POE"),
        "utp_ends": confirmed(2, "EV-ENDS"),
    }
    evaluated = evaluate_pattern_scope(
        project,
        plan(project, PatternBinding("camera", pattern, facts)),
        registry_context=registry_context(pattern),
        ethernet_scope=topology,
    )
    required = {line.key for line in evaluated.proposal.lines if line.required}
    assert {item.id for item in topology.links} <= required
    assert "at239:cable:CAT6-IN" in required
    assert (
        next(
            line for line in evaluated.proposal.lines if line.key == "at239:cable:CAT6-IN"
        ).quantity
        is None
    )
    assert evaluated.payload["ethernet"] is not None
    assert evaluated.payload["ethernet"]["materials"][0]["requiredLengthM"] is not None
    assert not evaluated.payload["commercialReady"]
    rejected = review(evaluated.proposal, (ReviewAction("LINK-CAM-2", "reject"),))
    assert rejected.status == "blocked"
    with pytest.raises(ValueError, match="Topology is required"):
        evaluate_pattern_scope(
            project,
            plan(project, PatternBinding("camera", pattern, facts)),
            registry_context=registry_context(pattern),
            previous=rejected,
        )


@pytest.mark.parametrize("length", ["1e309", "1e-999"])
def test_topology_decimal_range_fails_closed_before_json_payload(length: str) -> None:
    fixture = json.loads((ROOT / "demo/ethernet/fixture.json").read_text(encoding="utf-8"))
    altered = copy.deepcopy(fixture["topology"])
    altered["runs"][0]["sectionLengthsM"] = [length]
    altered["runs"][0]["slackPerEndM"] = "0"
    altered["runs"][0]["wasteFraction"] = "0"
    with pytest.raises(ValueError, match="Topology length is not reviewable"):
        evaluate_ethernet_scope(fixture["catalog"], altered)

    valid = evaluate_ethernet_scope(fixture["catalog"], fixture["topology"])
    injected = replace(
        valid,
        material_totals_complete=True,
        materials=(replace(valid.materials[0], required_length_m=length),),
    )
    with pytest.raises(ValueError, match="Topology length is not reviewable"):
        evaluate_scope(intake("camera", 1), None, ethernet_scope=injected)

    reviewable = replace(valid, material_totals_complete=True)
    payload = evaluate_scope(intake("camera", 1), None, ethernet_scope=reviewable).payload
    json.dumps(payload, allow_nan=False)
    assert all(line["quantity"] is None or line["quantity"] > 0 for line in payload["lines"])


def test_read_only_relate_pattern_rule_paths() -> None:
    pattern = BY_NAME["poe-camera"]
    project = intake("camera", 8)
    binding = PatternBinding(
        "camera",
        pattern,
        {
            "application": confirmed(True, "EV-APPLICATION"),
            "wired_run": confirmed(True, "EV-WIRED"),
            "mount_required": confirmed(False, "EV-MOUNT"),
            "poe_source": confirmed(True, "EV-POE"),
            "utp_ends": confirmed(2, "EV-ENDS"),
        },
    )
    with tempfile.TemporaryDirectory(prefix="at240-pattern-") as directory:
        connection = relate.connect(str(Path(directory) / "patterns.db"))
        seed_patterns(connection, [pattern])
        source = "\n".join(
            line
            for line in (ROOT / "demo/ethernet/seed.cypher").read_text().splitlines()
            if not line.lstrip().startswith("//")
        )
        for statement in source.split(";"):
            if statement.strip():
                connection.execute(statement)
        before = connection.execute("MATCH (n) RETURN count(n) AS n").single()["n"]
        reader = RelateEvidenceReader(connection, "estimate-hackathon-v1")
        paths = reader.resolve_pattern_rules(pattern["id"], ("AT247-CAMERA_UTP",))
        assert paths[0].status == "rule_context"
        assert paths[0].source_ref == pattern["sourceRef"]
        assert reader.resolve_pattern_rules(pattern["id"], ("MISSING-RULE",))[0].status == "unknown"
        evaluated = evaluate_pattern_scope(
            project,
            plan(project, binding),
            reader,
            registry_context=registry_context(pattern),
        )
        line = next(line for line in evaluated.payload["lines"] if line["key"] == "at247:item:utp")
        assert line["graphRulePaths"][0]["status"] == "rule_context"
        assert not evaluated.payload["commercialReady"]
        fixture = json.loads((ROOT / "demo/ethernet/fixture.json").read_text())
        topology = evaluate_ethernet_scope(fixture["catalog"], fixture["topology"])
        with_topology = evaluate_pattern_scope(
            project,
            plan(project, binding),
            reader,
            registry_context=registry_context(pattern),
            ethernet_scope=topology,
            ethernet_dataset_id="at-239-synthetic-v1",
        )
        assert with_topology.payload["ethernet"] is not None
        assert len(with_topology.payload["ethernet"]["graphLinkPaths"]) == 4
        assert all(
            path["status"] == "required_link_context"
            for path in with_topology.payload["ethernet"]["graphLinkPaths"]
        )
        overlapping = copy.deepcopy(fixture["topology"])
        overlapping["runs"][0]["evidenceId"] = overlapping["endpoints"][0]["evidenceId"]
        duplicate_evidence = evaluate_ethernet_scope(fixture["catalog"], overlapping)
        assert len(duplicate_evidence.links[0].evidence_ids) == len(
            set(duplicate_evidence.links[0].evidence_ids)
        )
        direct = evaluate_scope(project, None, reader, ethernet_scope=duplicate_evidence)
        patterned = evaluate_pattern_scope(
            project,
            plan(project, binding),
            reader,
            registry_context=registry_context(pattern),
            ethernet_scope=duplicate_evidence,
        )
        for result in (direct, patterned):
            line = next(line for line in result.payload["lines"] if line["key"] == "LINK-CAM-1")
            assert len(line["evidence"]) == len({item["id"] for item in line["evidence"]})
            assert not result.payload["commercialReady"]
        supplied_duplicate = replace(
            duplicate_evidence,
            links=(
                replace(duplicate_evidence.links[0], evidence_ids=("EV-CAM-1", "EV-CAM-1")),
                *duplicate_evidence.links[1:],
            ),
        )
        evaluate_scope(project, None, reader, ethernet_scope=supplied_duplicate)
        after = connection.execute("MATCH (n) RETURN count(n) AS n").single()["n"]
        assert before == after
        connection.close()


def test_unsupported_specialty_keeps_user_need_without_invented_materials() -> None:
    project = intake("uncovered_trade", None)
    result = evaluate_scope(project, None)
    assert result.proposal.status == "pending_specialist"
    assert [line.key for line in result.proposal.lines] == ["uncovered_trade"]
    assert result.proposal.lines[0].quantity is None
    assert not result.payload["commercialReady"]
