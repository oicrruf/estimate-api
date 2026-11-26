"""AT-233: synthetic AT-229 graph, read-only Relate queries, and domain regressions."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import relate

from estimate_api.inventory.relate_reader import read_inventory
from estimate_api.inventory.risk import (
    Dependency,
    PoolClaim,
    RiskLevel,
    RiskThresholds,
    StockClaim,
    StockState,
    evaluate_inventory,
)

SEED = Path(__file__).resolve().parents[2] / "demo/fixtures/seed.cypher"
NOW = datetime(2026, 11, 26, 12, tzinfo=UTC)


def _literal(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def _seed(connection: object) -> None:
    for line in SEED.read_text(encoding="utf-8").splitlines():
        if line.startswith("//") or not line.strip():
            continue
        connection.execute(line.removesuffix(";"))  # type: ignore[attr-defined]


def _observation(connection: object, identifier: str, **fields: object) -> None:
    evidence_id = fields.pop("evidenceId")
    source = fields.pop("source")
    props = ", ".join(f"{key}: {_literal(value)}" for key, value in fields.items())
    connection.execute(  # type: ignore[attr-defined]
        f"MERGE (s:STOCK_OBSERVATION {{id: {_literal(identifier)}}}) SET s += {{{props}}}"
    )
    connection.execute(  # type: ignore[attr-defined]
        f"MERGE (e:EVIDENCE {{id: {_literal(evidence_id)}}}) "
        f"SET e.source = {_literal(source)}, e.datasetId = 'at233-synthetic'"
    )
    connection.execute(  # type: ignore[attr-defined]
        f"MATCH (s:STOCK_OBSERVATION {{id: {_literal(identifier)}}}), "
        f"(e:EVIDENCE {{id: {_literal(evidence_id)}}}) MERGE (s)-[:SUPPORTED_BY]->(e)"
    )


def _confirmed_graph(connection: object) -> None:
    for offer, supplier in (
        ("OFF-CAM-A", "Proveedor ficticio A"),
        ("OFF-CAM-B", "Proveedor ficticio B"),
    ):
        _observation(
            connection,
            f"STOCK-{offer}",
            offerId=offer,
            state="supplier_confirmed",
            quantity=2,
            observedAt="2026-11-26T10:00:00Z",
            validUntil="2026-11-27T10:00:00Z",
            supplierId=supplier,
            branchId=f"BR-{offer}",
            source=f"confirmación sintética {offer}",
            evidenceId=f"EV-STOCK-{offer}",
            restockAt="2026-12-01T10:00:00Z",
        )
    _observation(
        connection,
        "STOCK-POOL",
        poolId="POOL-CAM-POE",
        state="supplier_confirmed",
        quantity=2,
        observedAt="2026-11-26T10:00:00Z",
        validUntil="2026-11-27T10:00:00Z",
        source="confirmación sintética pool",
        evidenceId="EV-STOCK-POOL",
    )


def test_at229_public_stock_stays_unknown_and_read_is_pure(tmp_path: Path) -> None:
    connection = relate.connect(str(tmp_path / "public.db"))
    _seed(connection)
    before = connection.execute("MATCH (n) RETURN count(n) AS n").single()["n"]
    claims, caps, dependencies = read_inventory(connection, "CAM-POE")
    result = evaluate_inventory(4, claims, caps, dependencies, now=NOW)
    assert result.risk == RiskLevel.UNKNOWN
    assert result.confirmed_quantity is None
    assert result.shortage is None
    assert all(item.reason == "PUBLIC_ONLY" for item in result.claims)
    assert len(result.dependencies) == 1
    assert result.dependencies[0].evidence_id == "EV-POOL-CAM"
    assert connection.execute("MATCH (n) RETURN count(n) AS n").single()["n"] == before
    connection.close()


def test_confirmed_pool_2_of_4_and_reopened_sufficient_2(tmp_path: Path) -> None:
    path = str(tmp_path / "confirmed.db")
    connection = relate.connect(path)
    _seed(connection)
    _confirmed_graph(connection)
    connection.close()
    connection = relate.connect(path)
    claims, caps, dependencies = read_inventory(connection, "CAM-POE")
    limited = evaluate_inventory(4, claims, caps, dependencies, now=NOW)
    assert limited.confirmed_quantity == 2
    assert limited.coverage == 0.5
    assert limited.shortage == 2
    assert limited.risk == RiskLevel.HIGH
    assert "SHARED_POOL_CAP" in limited.reasons
    assert limited.claims[0].claim.branch_id == "BR-OFF-CAM-A"
    assert limited.claims[0].claim.restock_at is not None
    sufficient = evaluate_inventory(2, claims, caps, dependencies, now=NOW)
    assert sufficient.risk == RiskLevel.LOW
    assert sufficient.confirmed_quantity == 2
    assert sufficient.shortage == 0
    connection.close()


def test_stale_and_unverified_pool_fail_closed(tmp_path: Path) -> None:
    connection = relate.connect(str(tmp_path / "stale.db"))
    _seed(connection)
    _confirmed_graph(connection)
    connection.execute(
        "MATCH (s:STOCK_OBSERVATION {id:'STOCK-OFF-CAM-B'}) "
        "SET s.validUntil = '2026-11-25T10:00:00Z'"
    )
    claims, caps, dependencies = read_inventory(connection, "CAM-POE")
    result = evaluate_inventory(4, claims, caps, dependencies, now=NOW)
    assert result.risk == RiskLevel.UNKNOWN
    assert result.confirmed_quantity is None
    assert "STALE_STOCK" in result.reasons
    connection.execute(
        "MATCH (s:STOCK_OBSERVATION {id:'STOCK-OFF-CAM-B'}) "
        "SET s.validUntil = '2026-11-27T10:00:00Z'"
    )
    connection.execute("MATCH (s:STOCK_OBSERVATION {id:'STOCK-POOL'}) SET s.state = 'published'")
    result = evaluate_inventory(4, *read_inventory(connection, "CAM-POE"), now=NOW)
    assert result.risk == RiskLevel.UNKNOWN
    assert "UNVERIFIED_SHARED_POOL" in result.reasons
    connection.close()


def test_unlinked_confirmation_cannot_support_supply(tmp_path: Path) -> None:
    connection = relate.connect(str(tmp_path / "unlinked.db"))
    _seed(connection)
    _confirmed_graph(connection)
    connection.execute(
        "MATCH (s:STOCK_OBSERVATION {id:'STOCK-OFF-CAM-A'})-[r:SUPPORTED_BY]->(:EVIDENCE) DELETE r"
    )
    result = evaluate_inventory(4, *read_inventory(connection, "CAM-POE"), now=NOW)
    assert result.risk == RiskLevel.UNKNOWN
    assert "UNSOURCED_CONFIRMATION" in result.reasons
    connection.close()


def test_distributor_correlation_never_implies_shared_stock(tmp_path: Path) -> None:
    connection = relate.connect(str(tmp_path / "distributor.db"))
    _seed(connection)
    _confirmed_graph(connection)
    connection.execute("MERGE (d:DISTRIBUTOR {id:'DIST-SYNTHETIC'})")
    for offer in ("OFF-CAM-A", "OFF-CAM-B"):
        connection.execute(
            "MERGE (e:EVIDENCE {id:'EV-DIST-" + offer + "'}) SET e.source = 'declaración sintética'"
        )
        connection.execute(
            "MATCH (o:OFFER {id:'" + offer + "'}), (d:DISTRIBUTOR {id:'DIST-SYNTHETIC'}) "
            "MERGE (o)-[r:DISTRIBUTED_BY]->(d) "
            "SET r.evidenceId = 'EV-DIST-" + offer + "', r.source = 'declaración sintética'"
        )
    claims, caps, dependencies = read_inventory(connection, "CAM-POE")
    assert {item.kind for item in dependencies} == {"shared_pool", "shared_distributor"}
    assert evaluate_inventory(4, claims, caps, dependencies, now=NOW).confirmed_quantity == 2
    # Distributor evidence alone warns of a dependency; it cannot cap independent claims.
    independent = tuple(
        StockClaim(
            c.offer_id,
            c.supplier_id,
            c.branch_id,
            c.state,
            c.quantity,
            c.observed_at,
            c.valid_until,
            c.source,
            c.evidence_id,
        )
        for c in claims
    )
    only_distributor = tuple(d for d in dependencies if d.kind == "shared_distributor")
    result = evaluate_inventory(4, independent, (), only_distributor, now=NOW)
    assert result.confirmed_quantity == 4
    assert result.risk == RiskLevel.LOW
    assert "SHARED_DISTRIBUTOR" in result.reasons
    connection.execute("MATCH (e:EVIDENCE {id:'EV-DIST-OFF-CAM-B'}) DELETE e")
    assert not any(d.kind == "shared_distributor" for d in read_inventory(connection, "CAM-POE")[2])
    connection.close()


def test_unknown_never_becomes_zero_and_thresholds_are_configurable() -> None:
    unknown = StockClaim("O", "S", None, StockState.UNKNOWN, None, None, None, None, None)
    result = evaluate_inventory(4, (unknown,), (), (), now=NOW)
    assert (result.confirmed_quantity, result.coverage, result.shortage) == (None, None, None)
    fresh = StockClaim(
        "O", "S", None, StockState.RESERVED, 3, NOW, NOW, "synthetic reservation", "EV-RES"
    )
    result = evaluate_inventory(
        4,
        (fresh,),
        (),
        (),
        now=NOW,
        thresholds=RiskThresholds(medium_coverage=1, high_coverage=0.5),
    )
    assert (result.risk, result.shortage) == (RiskLevel.MEDIUM, 1)
    with pytest.raises(ValueError):
        evaluate_inventory(4, (fresh, fresh), (), (), now=NOW)
    with pytest.raises(ValueError):
        RiskThresholds(medium_coverage=0.5, high_coverage=0.5)


def test_shared_pool_requires_confirmed_cap_and_evidence() -> None:
    fresh = StockClaim(
        "O", "S", None, StockState.SUPPLIER_CONFIRMED, 4, NOW, NOW, "synthetic", "EV", "POOL"
    )
    public = PoolClaim("POOL", StockState.PUBLISHED, 2, NOW, NOW, "listing", "EV-P")
    result = evaluate_inventory(4, (fresh,), (public,), (), now=NOW)
    assert result.risk == RiskLevel.UNKNOWN
    assert result.confirmed_quantity is None
    with pytest.raises(ValueError):
        evaluate_inventory(
            4,
            (fresh,),
            (),
            (Dependency("O", "MISSING", "shared_distributor", "D", "EV", "src"),),
            now=NOW,
        )
