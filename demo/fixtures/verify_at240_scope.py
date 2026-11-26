#!/usr/bin/env python3
"""Exercise AT-240's read-only adapter with an isolated AT-229 Relate seed."""

import copy
import json
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

import relate
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from estimate_api.discovery.engine import diff_proposals, discover, review  # noqa: E402
from estimate_api.discovery.evidence import RelateEvidenceReader  # noqa: E402
from estimate_api.discovery.hardware_adapter import evaluate_hardware_scope  # noqa: E402
from estimate_api.discovery.models import (  # noqa: E402
    KnowledgePackage,
    Need,
    ProjectIntake,
    ReviewAction,
    Rule,
)
from estimate_api.discovery.registry_adapter import (  # noqa: E402
    RegistryContext,
    resolve_pattern_coverage,
)
from estimate_api.discovery.service import evaluate_scope, to_review_payload  # noqa: E402

BASE = Path(__file__).resolve().parent


def main() -> None:
    data = json.loads((BASE / "at-240-discovery.json").read_text(encoding="utf-8"))
    project = data["project"]
    package_data = data["package"]
    intake = ProjectIntake(**{**project, "needs": tuple(Need(**need) for need in project["needs"])})
    package = KnowledgePackage(
        **{
            **package_data,
            "rules": tuple(
                Rule(**{**rule, "evidence_ids": tuple(rule.get("evidence_ids", ()))})
                for rule in package_data["rules"]
            ),
        }
    )
    project_document = json.loads(
        (ROOT / "fixtures/valid/cameras.json").read_text(encoding="utf-8")
    )
    registry = copy.deepcopy(
        json.loads(
            (ROOT / "fixtures/knowledge/registry-synthetic.json").read_text(encoding="utf-8")
        )
    )
    registry["packages"][0]["review"].update(
        state="verified",
        reviewerRef="synthetic://reviewer",
        evidenceRefs=["synthetic://review"],
    )
    registry_context = RegistryContext(
        project_document,
        registry,
        "fictional-camera",
        {"kind": "project", "id": "camera:project"},
    )
    hardware = json.loads((ROOT / "demo/hardware/fixture.json").read_text(encoding="utf-8"))
    confirmed_hardware = evaluate_hardware_scope(
        hardware["catalog"], hardware["routes"]["confirmed"]
    )
    unknown_hardware = evaluate_hardware_scope(hardware["catalog"], hardware["routes"]["unknown"])
    source = "\n".join(
        line
        for line in (BASE / "seed.cypher").read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("//")
    )
    with tempfile.TemporaryDirectory(prefix="at240-relate-") as directory:
        connection = relate.connect(str(Path(directory) / "synthetic.db"))
        for statement in source.split(";"):
            if statement.strip():
                connection.execute(statement)
        before = connection.execute("MATCH (n) RETURN count(n) AS n").single()["n"]
        reader = RelateEvidenceReader(connection, "estimate-hackathon-v1")
        evaluated = evaluate_scope(
            intake,
            package,
            reader,
            registry_context=registry_context,
            hardware_scope=confirmed_hardware,
        )
        assert evaluated.payload["coverage"]["reasons"] == ["reviewed_package_missing"]
        assert {line["key"] for line in evaluated.payload["lines"]} == {
            need.key for need in intake.needs
        }
        proposal = discover(intake, package)
        coverage = resolve_pattern_coverage(intake, package, registry_context)
        rendered = to_review_payload(
            proposal, reader, coverage=coverage, hardware_scope=confirmed_hardware
        )
        lines = {line["key"]: line for line in rendered["lines"]}
        assert lines["ethernet_link"]["evidenceStatus"] == "capability_context"
        assert lines["ethernet_link"]["evidence"][0]["id"] == "EV-CAM-POE"
        assert lines["termination"]["evidenceStatus"] == "unknown"
        assert rendered["hardware"]["missing"][0]["quantity"] == 2
        assert not rendered["commercialReady"]
        blocked = review(proposal, (ReviewAction("termination", "reject"),))
        assert blocked.status == "blocked" and not blocked.commercial_ready
        reviewed = review(proposal, (ReviewAction("termination", "approve"),))
        assert next(line for line in reviewed.lines if line.key == "termination").quantity == 16
        changed_needs = tuple(
            replace(need, quantity=12) if need.key == "camera" else need for need in intake.needs
        )
        changed = diff_proposals(reviewed, discover(replace(intake, needs=changed_needs), package))
        assert ("termination", "changed") in changed.changes
        assert next(line for line in changed.lines if line.key == "termination").quantity == 24
        assert {line.key for line in changed.lines if line.required} == {
            line.key for line in proposal.lines if line.required
        }
        coverage = resolve_pattern_coverage(intake, package, registry_context)
        changed_payload = to_review_payload(
            changed,
            reader,
            coverage=coverage,
            hardware_scope=unknown_hardware,
        )
        assert changed_payload["hardware"]["lines"] == []
        assert changed_payload["hardware"]["missing"] == []
        assert not changed_payload["commercialReady"]
        schema = json.loads(
            (ROOT / "src/estimate_api/discovery/schemas/scope-review.v1.schema.json").read_text(
                encoding="utf-8"
            )
        )
        Draft202012Validator(schema).validate(json.loads(json.dumps(changed_payload)))
        assert reader.resolve(("EV-NOT-PRESENT",))[0].status == "unknown"
        after = connection.execute("MATCH (n) RETURN count(n) AS n").single()["n"]
        assert before == after == 60
        connection.close()
    print("AT-240: input→proposal→review→revalidation OK; 60 graph nodes unchanged")


if __name__ == "__main__":
    main()
