"""Contrato sintético del paquete de ferretería AT-238."""

import copy
import json
import tempfile
from pathlib import Path

import relate

from estimate_api.hardware import evaluate_route

BASE = Path(__file__).resolve().parents[1] / "demo" / "hardware"
FIXTURE = json.loads((BASE / "fixture.json").read_text(encoding="utf-8"))


def test_confirmed_route_and_missing_connector() -> None:
    result = evaluate_route(FIXTURE["catalog"], FIXTURE["routes"]["confirmed"])
    assert result["status"] == "REVIEW_REQUIRED"
    assert {line["family"]: line["quantity"] for line in result["lines"]} == {
        "emt": 2,
        "coupling": 1,
        "support": 3,
    }
    assert result["missing"] == [
        {
            "family": "connector",
            "quantity": 2,
            "ruleId": "RULE-CONFIRMED-ENTRIES",
            "evidenceIds": ["EV-ROUTE-CONFIRMED"],
            "alternatives": [{"id": "GEN-CONNECTOR-1", "evidenceId": "EV-CAT-CONNECTOR-1"}],
        }
    ]
    assert all(line["evidence_ids"] and line["rule_id"] for line in result["lines"])
    assert not any(line["family"] in ("lb", "outlet") for line in result["lines"])
    assert result["professionalValidationRequired"]


def test_diameter_change_invalidates_selected_accessories() -> None:
    route = copy.deepcopy(FIXTURE["routes"]["confirmed"])
    route["diameter"] = "3/4"
    route["selectedAccessories"]["connector"] = "GEN-CONNECTOR-1"
    result = evaluate_route(FIXTURE["catalog"], route)
    assert result["lines"][0]["material_id"] == "GEN-EMT-3-4"
    assert {item["id"] for item in result["incompatible"]} == {
        "GEN-COUPLING-1",
        "GEN-CONNECTOR-1",
        "GEN-SUPPORT-1",
    }
    assert {item["alternatives"][0]["id"] for item in result["incompatible"]} == {
        "GEN-COUPLING-3-4",
        "GEN-CONNECTOR-3-4",
        "GEN-SUPPORT-3-4",
    }
    assert all(item["evidenceIds"] for item in result["incompatible"])


def test_unknown_route_and_explicit_conditions() -> None:
    result = evaluate_route(FIXTURE["catalog"], FIXTURE["routes"]["unknown"])
    assert result["status"] == "PENDING" and not result["lines"]
    route = copy.deepcopy(FIXTURE["routes"]["confirmed"])
    route["lbRequired"] = True
    route["confirmedLbPoints"] = 1
    result = evaluate_route(FIXTURE["catalog"], route)
    assert any(item["family"] == "lb" for item in result["missing"])
    assert not any(item["family"] == "outlet" for item in result["missing"])


def _statements() -> list[str]:
    source = "\n".join(
        line
        for line in (BASE / "seed.cypher").read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("//")
    )
    return [part.strip() for part in source.split(";") if part.strip()]


def test_real_relate_graph_idempotent_and_evidenced() -> None:
    with tempfile.TemporaryDirectory(prefix="at238-relate-") as directory:
        connection = relate.connect(str(Path(directory) / "hardware.db"))
        for statement in _statements():
            connection.execute(statement)
        nodes = connection.execute("MATCH (n) RETURN count(n) AS n").single()["n"]
        edges = connection.execute("MATCH ()-[r]->() RETURN count(r) AS n").single()["n"]
        for statement in _statements():
            connection.execute(statement)
        assert connection.execute("MATCH (n) RETURN count(n) AS n").single()["n"] == nodes
        assert connection.execute("MATCH ()-[r]->() RETURN count(r) AS n").single()["n"] == edges
        rows = connection.execute(
            'MATCH (a:ACCESSORY)-[:FITS_DIAMETER]->(s:SPEC {diameter: "3/4"}), '
            "(a)-[:SUPPORTED_BY]->(e:EVIDENCE) "
            "RETURN a.id AS accessoryId, e.id AS evidenceId ORDER BY accessoryId"
        ).data()
        assert {row["accessoryId"] for row in rows} == {
            "GEN-COUPLING-3-4",
            "GEN-CONNECTOR-3-4",
            "GEN-SUPPORT-3-4",
        }
        assert all(row["evidenceId"].startswith("EV-CAT-") for row in rows)
        route_path = connection.execute(
            'MATCH (s:INSTALLATION_SEGMENT {id: "SEG-DEMO"})-[:REQUIRES]->'
            "(r:REQUIREMENT)-[:SUPPORTED_BY]->(e:EVIDENCE) "
            "RETURN r.id AS requirementId, e.id AS evidenceId ORDER BY requirementId"
        ).data()
        assert len(route_path) == 3
        assert {row["evidenceId"] for row in route_path} == {"EV-ROUTE-CONFIRMED"}
        connection.close()
