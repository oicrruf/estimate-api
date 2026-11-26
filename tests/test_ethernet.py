"""AT-239: mediciones sintéticas y caminos de evidencia en Relate real."""

import copy
import json
import tempfile
from pathlib import Path

import relate

from estimate_api.ethernet import evaluate_topology

BASE = Path(__file__).resolve().parents[1] / "demo" / "ethernet"
FIXTURE = json.loads((BASE / "fixture.json").read_text(encoding="utf-8"))


def test_required_links_and_measured_material() -> None:
    result = evaluate_topology(FIXTURE["catalog"], FIXTURE["topology"])
    assert {link["id"] for link in result["links"]} == {
        "LINK-CAM-1",
        "LINK-CAM-2",
        "LINK-MESH-2",
        "LINK-UPLINK",
    }
    assert result["materials"] == [
        {
            "cableId": "CAT6-IN",
            "requiredLengthM": "23.10",
            "commercialRolls": 1,
            "purchasedLengthM": "305",
            "recoverableRemainderM": "281.90",
            "ruleId": "RULE-SUM-CONFIRMED-ROUTES",
            "evidenceIds": ["EV-CAM-1", "EV-CAT6-IN", "EV-RUN-CAM-1"],
        }
    ]
    assert result["status"] == "PENDING"
    assert all(item["evidenceIds"] for item in result["pending"])
    assert result["professionalValidationRequired"]


def test_changed_count_adds_links_without_fictitious_meters() -> None:
    topology = copy.deepcopy(FIXTURE["topology"])
    topology["endpoints"].extend(
        {"id": f"CAM-{number}", "medium": "poe_ethernet", "evidenceId": f"EV-CAM-{number}"}
        for number in range(3, 11)
    )
    result = evaluate_topology(FIXTURE["catalog"], topology)
    assert len(result["links"]) == 12
    assert result["materials"][0]["requiredLengthM"] == "23.10"
    assert all(
        link["requiredLengthM"] is None
        for link in result["links"]
        if link["id"] in {"LINK-CAM-9", "LINK-CAM-10"}
    )


def test_eight_to_ten_poe_cameras_keep_unknown_lengths_pending() -> None:
    topology = copy.deepcopy(FIXTURE["topology"])
    topology["endpoints"] = [
        {"id": f"CAM-{number}", "medium": "poe_ethernet", "evidenceId": f"EV-CAM-{number}"}
        for number in range(1, 9)
    ]
    topology["runs"] = []
    first = evaluate_topology(FIXTURE["catalog"], topology)
    assert len(first["links"]) == 9 and first["materials"] == []
    topology["endpoints"].extend(
        {"id": f"CAM-{number}", "medium": "poe_ethernet", "evidenceId": f"EV-CAM-{number}"}
        for number in (9, 10)
    )
    second = evaluate_topology(FIXTURE["catalog"], topology)
    assert len(second["links"]) == 11 and second["materials"] == []
    assert all(link["requiredLengthM"] is None for link in second["links"])


def test_cable_environment_termination_and_poe_port() -> None:
    topology = copy.deepcopy(FIXTURE["topology"])
    run = topology["runs"][0]
    run["environment"] = "exterior_uv"
    run["terminationIds"][1] = "RJ45-STRANDED"
    topology["ports"]["SW-1"]["poeCapable"] = False
    result = evaluate_topology(FIXTURE["catalog"], topology)
    assert {item["reason"] for item in result["incompatible"]} >= {
        "CABLE_ENVIRONMENT",
        "TERMINATION_MISMATCH",
        "POE_SOURCE_PORT_REQUIRED",
    }
    assert result["status"] == "REVIEW_REQUIRED"
    assert any(item["id"] == "CAT6-OUT" for item in FIXTURE["catalog"]["cables"])


def test_synthetic_confirmed_link_can_derive_without_claiming_certification() -> None:
    topology = copy.deepcopy(FIXTURE["topology"])
    topology["endpoints"] = [topology["endpoints"][0]]
    topology["runs"] = [topology["runs"][0]]
    topology["uplinkRequired"] = False
    run = topology["runs"][0]
    run.update(
        {
            "conduitOccupancyVerified": True,
            "bandwidthVerified": True,
            "poeBudgetVerified": True,
            "terminationCertificationVerified": True,
            "channelLimitVerified": True,
        }
    )
    result = evaluate_topology(FIXTURE["catalog"], topology)
    assert result["status"] == "DERIVED"
    assert result["pending"] == [] and result["incompatible"] == []
    assert result["materials"][0]["requiredLengthM"] == "23.10"
    assert result["professionalValidationRequired"] is True


def test_cca_and_wrong_endpoint_are_rejected_without_losing_measurement() -> None:
    topology = copy.deepcopy(FIXTURE["topology"])
    topology["runs"][0]["cableId"] = "CAT6-CCA"
    topology["ports"]["CAM-1-P"]["endpointId"] = "CAM-2"
    result = evaluate_topology(FIXTURE["catalog"], topology)
    assert {item["reason"] for item in result["incompatible"]} >= {
        "CABLE_CONSTRUCTION",
        "WRONG_ENDPOINT",
    }
    assert result["materials"][0]["requiredLengthM"] == "23.10"
    assert result["status"] == "REVIEW_REQUIRED"


def test_invalid_measurement_rejected() -> None:
    topology = copy.deepcopy(FIXTURE["topology"])
    topology["runs"][0]["sectionLengthsM"] = ["NaN"]
    try:
        evaluate_topology(FIXTURE["catalog"], topology)
    except ValueError as exc:
        assert "sectionLengthM" in str(exc)
    else:
        raise AssertionError("Se aceptó una longitud no finita")


def test_unconfirmed_route_with_tentative_lengths_has_no_purchase_quantity() -> None:
    topology = copy.deepcopy(FIXTURE["topology"])
    topology["runs"][0]["routeConfirmed"] = False
    result = evaluate_topology(FIXTURE["catalog"], topology)
    assert result["materials"] == []
    assert all(link["requiredLengthM"] is None for link in result["links"])


def test_commercial_rolls_allocate_individual_cuts() -> None:
    topology = copy.deepcopy(FIXTURE["topology"])
    first = topology["runs"][0]
    first["sectionLengthsM"] = ["200"]
    first["slackPerEndM"] = "0"
    first["wasteFraction"] = "0"
    first["cableCount"] = 2
    result = evaluate_topology(FIXTURE["catalog"], topology)
    material = result["materials"][0]
    assert material["requiredLengthM"] == "400"
    assert material["commercialRolls"] == 2
    assert material["purchasedLengthM"] == "610"


def _statements() -> list[str]:
    source = "\n".join(
        line
        for line in (BASE / "seed.cypher").read_text(encoding="utf-8").splitlines()
        if not line.startswith("//")
    )
    return [part.strip() for part in source.split(";") if part.strip()]


def test_real_relate_paths_and_idempotence() -> None:
    with tempfile.TemporaryDirectory(prefix="at239-relate-") as directory:
        conn = relate.connect(str(Path(directory) / "ethernet.db"))
        for statement in _statements():
            conn.execute(statement)
        counts = (
            conn.execute("MATCH (n) RETURN count(n) AS n").single()["n"],
            conn.execute("MATCH ()-[r]->() RETURN count(r) AS n").single()["n"],
        )
        for statement in _statements():
            conn.execute(statement)
        assert counts == (
            conn.execute("MATCH (n) RETURN count(n) AS n").single()["n"],
            conn.execute("MATCH ()-[r]->() RETURN count(r) AS n").single()["n"],
        )
        rows = conn.execute(
            "MATCH (e:ENDPOINT)-[:REQUIRES_LINK]->(l:NETWORK_LINK)-[:SUPPORTED_BY]->"
            "(v:EVIDENCE) RETURN e.id AS endpoint, l.id AS link, v.id AS evidence ORDER BY endpoint"
        ).data()
        assert {row["endpoint"] for row in rows} == {"CAM-1", "CAM-2", "MESH-2", "ROUTER"}
        assert all(row["evidence"].startswith("EV-") for row in rows)
        routes = conn.execute(
            "MATCH (l:NETWORK_LINK)-[:CONNECTS_TO]->(r:CABLE_RUN)-[:USES_CABLE]->"
            "(c:CABLE_TYPE)-[:SUPPORTED_BY]->(e:EVIDENCE) "
            "RETURN l.id AS link, c.id AS cable, e.id AS evidence ORDER BY link"
        ).data()
        assert routes == [
            {"link": "LINK-CAM-1", "cable": "CAT6-IN", "evidence": "EV-CAT6-IN"},
            {"link": "LINK-CAM-2", "cable": "CAT6-IN", "evidence": "EV-CAT6-IN"},
        ]
        conn.close()
