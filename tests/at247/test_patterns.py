"""Controles positivos y negativos de patrones ficticios AT-247."""

import copy
import json
from pathlib import Path

import relate

from estimate_api.knowledge.registry_v1 import validate_registry
from estimate_api.patterns.relate_seed import seed_patterns
from estimate_api.patterns.v1 import (
    Fact,
    Pattern,
    evaluate_emt_with_at238,
    expand,
    registry_reference,
)

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures/patterns/patterns.v1.json"
PATTERNS: list[Pattern] = json.loads(FIXTURE.read_text(encoding="utf-8"))["patterns"]
BY_NAME = {pattern["id"].split(":")[-1]: pattern for pattern in PATTERNS}


def fact(value: str | bool | int | None, evidence: str = "EV-SYNTH") -> Fact:
    return {"state": "confirmed", "value": value, "evidenceId": evidence}


def base() -> dict[str, Fact]:
    return {"application": fact(True, "EV-APPLICATION")}


def items(result: object) -> set[str]:
    return {candidate["itemId"].split(":")[-1] for candidate in result.candidates}  # type: ignore[attr-defined]


def test_camera_dependencies_and_at265_reference() -> None:
    inputs = base() | {
        "wired_run": fact(True, "EV-WIRED"),
        "mount_required": fact(True, "EV-MOUNT"),
        "poe_source": fact(True, "EV-POE"),
        "utp_ends": fact(2, "EV-ENDS"),
    }
    result = expand(BY_NAME["poe-camera"], inputs)
    assert result.status == "DERIVED"
    assert items(result) == {"utp", "utp-connector", "link-test", "camera-mount", "poe-power"}
    connector = next(c for c in result.candidates if c["itemId"].endswith("utp-connector"))
    assert connector["quantity"] == 2
    assert "EV-ENDS" in connector["evidenceIds"]
    assert "EV-WIRED" in connector["evidenceIds"]
    assert connector["sourceRefs"] == ["synthetic://at-247/patterns/1.0.0"]
    assert registry_reference(BY_NAME["poe-camera"]) == {
        "id": "at247:pattern:poe-camera",
        "category": "fictional-camera",
        "ref": "synthetic://at-247/patterns/1.0.0",
    }
    assert result.professional_validation_required


def test_at265_registry_accepts_all_pattern_references() -> None:
    registry_path = FIXTURE.parents[1] / "knowledge/registry-synthetic.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    package = registry["packages"][0]
    package["applicability"]["categories"] = [p["category"] for p in PATTERNS]
    package["installationPatterns"] = [registry_reference(p) for p in PATTERNS]
    assert validate_registry(registry).valid


def test_mesh_branches_and_unknown() -> None:
    wired = expand(
        BY_NAME["mesh"],
        base()
        | {
            "backhaul": fact("wired"),
            "mount_required": fact(False),
            "power_required": fact(False),
            "utp_ends": fact(2),
        },
    )
    assert wired.status == "DERIVED"
    assert {"utp", "utp-connector", "link-test"} <= items(wired)
    assert "wireless-survey" not in items(wired)
    wireless = expand(
        BY_NAME["mesh"],
        base()
        | {
            "backhaul": fact("wireless"),
            "mount_required": fact(False),
            "power_required": fact(False),
        },
    )
    assert {"wireless-survey", "wireless-test"} <= items(wireless)
    assert "utp" not in items(wireless)
    unknown = expand(
        BY_NAME["mesh"],
        base()
        | {
            "backhaul": {"state": "unknown", "value": None, "evidenceId": None},
        },
    )
    assert unknown.status == "PENDING"
    assert "backhaul" in unknown.pending
    assert "utp" not in items(unknown)
    assert "wireless-survey" not in items(unknown)


def test_lb_and_outlet_need_confirmed_design_and_count() -> None:
    route = expand(
        BY_NAME["emt-route"],
        base()
        | {
            "route_measured": fact(False),
            "lb_required": {"state": "assumed", "value": True, "evidenceId": None},
        },
    )
    assert "lb" not in items(route) and "lb_required" in route.pending
    confirmed = expand(
        BY_NAME["emt-route"],
        base()
        | {
            "route_measured": fact(True),
            "lb_required": fact(True),
            "lb_points": fact(1),
        },
    )
    assert {"lb", "at238-route-evaluation"} <= items(confirmed)
    enclosure = expand(
        BY_NAME["enclosure"],
        base()
        | {
            "mount_required": fact(False),
            "interior_outlet_required": fact(True),
            "outlet_points": fact(1),
            "power_required": fact(False),
        },
    )
    assert "interior-outlet" in items(enclosure)
    missing_count = expand(
        BY_NAME["enclosure"],
        base()
        | {
            "mount_required": fact(False),
            "interior_outlet_required": fact(True),
            "power_required": fact(False),
        },
    )
    assert "interior-outlet" not in items(missing_count)
    assert "outlet_points" in missing_count.pending


def test_at238_route_evaluator_requires_matching_evidence() -> None:
    hardware_path = FIXTURE.parents[2] / "demo/hardware/fixture.json"
    hardware = json.loads(hardware_path.read_text(encoding="utf-8"))
    inputs = base() | {
        "route_measured": fact(True, "EV-ROUTE-CONFIRMED"),
        "lb_required": fact(False),
    }
    _, derived = evaluate_emt_with_at238(
        BY_NAME["emt-route"], inputs, hardware["catalog"], hardware["routes"]["confirmed"]
    )
    assert derived is not None
    assert next(line for line in derived["lines"] if line["family"] == "emt")["quantity"] == 2
    assert (
        next(line for line in derived["lines"] if line["family"] == "emt")["evidence_ids"][0]
        == "EV-ROUTE-CONFIRMED"
    )
    wrong = copy.deepcopy(hardware["routes"]["confirmed"])
    wrong["evidenceId"] = "EV-OTHER"
    _, blocked = evaluate_emt_with_at238(BY_NAME["emt-route"], inputs, hardware["catalog"], wrong)
    assert blocked is None
    unapproved = dict(inputs)
    unapproved["application"] = {"state": "unknown", "value": None, "evidenceId": None}
    _, blocked = evaluate_emt_with_at238(
        BY_NAME["emt-route"], unapproved, hardware["catalog"], hardware["routes"]["confirmed"]
    )
    assert blocked is None
    with_lb = copy.deepcopy(hardware["routes"]["confirmed"])
    with_lb["lbRequired"] = True
    with_lb["confirmedLbPoints"] = 1
    _, blocked = evaluate_emt_with_at238(BY_NAME["emt-route"], inputs, hardware["catalog"], with_lb)
    assert blocked is None
    with_lb_facts = inputs | {"lb_required": fact(True), "lb_points": fact(1)}
    _, derived_lb = evaluate_emt_with_at238(
        BY_NAME["emt-route"], with_lb_facts, hardware["catalog"], with_lb
    )
    assert derived_lb is not None
    assert any(missing["family"] == "lb" for missing in derived_lb["missing"])


def test_cycle_dedup_and_limits() -> None:
    pattern = copy.deepcopy(BY_NAME["power"])
    first = pattern["dependencies"][0]
    duplicate = copy.deepcopy(first)
    duplicate["id"] = "at247:edge:duplicate"
    duplicate["ruleId"] = "AT247-DUPLICATE"
    pattern["dependencies"].append(duplicate)
    pattern["dependencies"].append(
        {
            **first,
            "id": "at247:edge:cycle",
            "fromId": first["toId"],
            "toId": pattern["rootId"],
            "ruleId": "AT247-CYCLE",
            "condition": None,
        }
    )
    result = expand(pattern, base() | {"power_required": fact(True), "test_required": fact(False)})
    assert len([c for c in result.candidates if c["itemId"] == first["toId"]]) == 1
    assert result.cycles
    pattern["maxEdges"] = 1
    limited = expand(pattern, base() | {"power_required": fact(True)})
    assert limited.status == "LIMIT_REACHED" and limited.candidates == ()
    pattern["maxEdges"] = 64
    pattern["maxDepth"] = 1
    assert expand(pattern, base() | {"power_required": fact(True)}).status == "LIMIT_REACHED"


def test_conflicting_quantities_remain_pending() -> None:
    pattern = copy.deepcopy(BY_NAME["power"])
    first = pattern["dependencies"][0]
    pattern["dependencies"].append(
        {
            **first,
            "id": "at247:edge:conflicting-count",
            "quantityFact": "count",
        }
    )
    result = expand(pattern, base() | {"power_required": fact(True), "count": fact(2)})
    assert result.status == "PENDING"
    assert "quantity_conflict:at247:item:power-source" in result.pending
    assert "power-source" not in items(result)
    assert result.candidates == ()


def test_unknown_route_fixture_does_not_invoke_at238() -> None:
    hardware_path = FIXTURE.parents[2] / "demo/hardware/fixture.json"
    hardware = json.loads(hardware_path.read_text(encoding="utf-8"))
    inputs = base() | {
        "route_measured": {"state": "unknown", "value": None, "evidenceId": None},
        "lb_required": fact(False),
    }
    expansion, derived = evaluate_emt_with_at238(
        BY_NAME["emt-route"], inputs, hardware["catalog"], hardware["routes"]["unknown"]
    )
    assert expansion.status == "PENDING"
    assert "at238-route-evaluation" not in items(expansion)
    assert derived is None


def test_relate_seed_idempotent_and_evidence_path(tmp_path: Path) -> None:
    conn = relate.connect(str(tmp_path / "patterns.db"))
    conn.execute("MERGE (n:FOREIGN_DATA {id: 'untouched'})")
    seed_patterns(conn, PATTERNS)
    nodes = conn.execute("MATCH (n) RETURN count(n) AS n").single()["n"]
    edges = conn.execute("MATCH ()-[r]->() RETURN count(r) AS n").single()["n"]
    seed_patterns(conn, PATTERNS)
    assert conn.execute("MATCH (n) RETURN count(n) AS n").single()["n"] == nodes
    assert conn.execute("MATCH ()-[r]->() RETURN count(r) AS n").single()["n"] == edges
    assert conn.execute("MATCH (n:FOREIGN_DATA) RETURN count(n) AS n").single()["n"] == 1
    rows = conn.execute(
        "MATCH (p:INSTALLATION_PATTERN {id: 'at247:pattern:mesh'})-[:USES_RULE]->"
        "(r:PATTERN_RULE)-[:SUPPORTED_BY]->(s:PATTERN_SOURCE) "
        "RETURN r.id AS rule, s.id AS source"
    ).data()
    assert any(
        row["rule"] == "AT247-MESH_WIRED" and row["source"] == "synthetic://at-247/patterns/1.0.0"
        for row in rows
    )
    dependency_rows = conn.execute(
        "MATCH (p:INSTALLATION_PATTERN {id: 'at247:pattern:mesh'})-[:HAS_ROOT]->"
        "(root:PATTERN_ITEM)-[d:PATTERN_REQUIRES]->(item:PATTERN_ITEM) "
        "RETURN root.id AS root, d.ruleId AS rule, item.id AS item"
    ).data()
    assert {
        "root": "at247:item:mesh",
        "rule": "AT247-MESH_WIRED",
        "item": "at247:item:utp",
    } in dependency_rows
    conn.close()
    conn = relate.connect(str(tmp_path / "patterns.db"))
    assert conn.execute("MATCH (n) RETURN count(n) AS n").single()["n"] == nodes
    conn.close()
