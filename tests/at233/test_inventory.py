"""AT-233: synthetic AT-229 graph, read-only Relate queries, and domain regressions."""

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import relate

from demo.agent.graph import camera_stock_evidence
from estimate_api.inventory.relate_reader import read_inventory
from estimate_api.inventory.risk import (
    Dependency,
    PoolClaim,
    QuoteScope,
    RiskLevel,
    RiskThresholds,
    StockClaim,
    StockState,
    evaluate_inventory,
)

SEED = Path(__file__).resolve().parents[2] / "demo/fixtures/seed.cypher"
NOW = datetime(2026, 11, 26, 12, tzinfo=UTC)
SCOPE = QuoteScope("PROJECT-FICT-1", "QUOTE-FICT-1")


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


def test_at227_demo_public_capacity_is_not_at233_supplier_confirmation(tmp_path: Path) -> None:
    path = str(tmp_path / "demo-boundary.rl")
    connection = relate.connect(path)
    _seed(connection)
    connection.close()
    demo_rows = camera_stock_evidence(path, 2)
    assert len(demo_rows) == 1
    assert (demo_rows[0]["listedQuantity"], demo_rows[0]["poolCapacity"]) == (4, 2)
    connection = relate.connect(path, read_only=True)
    result = evaluate_inventory(2, *read_inventory(connection, "CAM-POE"), now=NOW)
    assert result.risk == RiskLevel.UNKNOWN
    assert (result.confirmed_quantity, result.coverage, result.shortage) == (None, None, None)
    assert all(item.reason == "PUBLIC_ONLY" for item in result.claims)
    connection.close()


def test_confirmed_pool_2_of_4_and_reopened_sufficient_2(tmp_path: Path) -> None:
    path = str(tmp_path / "confirmed.db")
    connection = relate.connect(path)
    _seed(connection)
    _confirmed_graph(connection)
    connection.close()
    connection = relate.connect(path, read_only=True)
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
    assert result.risk == RiskLevel.MEDIUM
    assert "SHARED_DISTRIBUTOR" in result.reasons
    assert "CORRELATED_DISTRIBUTOR_RISK" in result.reasons
    connection.execute("MATCH (e:EVIDENCE {id:'EV-DIST-OFF-CAM-B'}) DELETE e")
    assert not any(d.kind == "shared_distributor" for d in read_inventory(connection, "CAM-POE")[2])
    connection.close()


def test_unknown_never_becomes_zero_and_thresholds_are_configurable() -> None:
    unknown = StockClaim("O", "S", None, StockState.UNKNOWN, None, None, None, None, None)
    result = evaluate_inventory(4, (unknown,), (), (), now=NOW)
    assert (result.confirmed_quantity, result.coverage, result.shortage) == (None, None, None)
    fresh = StockClaim(
        "O",
        "S",
        None,
        StockState.SUPPLIER_CONFIRMED,
        3,
        NOW,
        NOW + timedelta(days=1),
        "synthetic confirmation",
        "EV-C",
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
        "O",
        "S",
        None,
        StockState.SUPPLIER_CONFIRMED,
        4,
        NOW,
        NOW + timedelta(days=1),
        "synthetic",
        "EV",
        "POOL",
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


def test_shared_pool_dependency_cannot_invent_pool_identity() -> None:
    fresh = StockClaim(
        "OFF-FICT-A",
        "SUP-FICT-A",
        None,
        StockState.SUPPLIER_CONFIRMED,
        2,
        NOW,
        NOW + timedelta(days=1),
        "confirmación ficticia",
        "EV-FICT-A",
    )
    second = replace(fresh, offer_id="OFF-FICT-B", supplier_id="SUP-FICT-B")
    linked = Dependency(
        "OFF-FICT-A", "OFF-FICT-B", "shared_pool", "POOL-FICT", "EV-POOL-FICT", "fuente ficticia"
    )
    with pytest.raises(ValueError, match="pool identities"):
        evaluate_inventory(4, (fresh, second), (), (linked,), now=NOW)
    with pytest.raises(ValueError, match="pool identities"):
        evaluate_inventory(
            4,
            (replace(fresh, pool_id="POOL-FICT"), second),
            (),
            (linked,),
            now=NOW,
        )


def test_relate_rejects_ambiguous_or_duplicate_offer_observations(tmp_path: Path) -> None:
    path = str(tmp_path / "ambiguous.db")
    connection = relate.connect(path)
    _seed(connection)
    _observation(
        connection,
        "STOCK-FICT-A",
        offerId="OFF-CAM-A",
        state="supplier_confirmed",
        quantity=2,
        observedAt="2026-11-26T10:00:00Z",
        validUntil="2026-11-27T10:00:00Z",
        source="confirmación ficticia",
        evidenceId="EV-FICT-A",
    )
    _observation(
        connection,
        "STOCK-FICT-B",
        offerId="OFF-CAM-A",
        poolId="POOL-CAM-POE",
        state="supplier_confirmed",
        quantity=2,
        observedAt="2026-11-26T10:00:00Z",
        validUntil="2026-11-27T10:00:00Z",
        source="confirmación ficticia",
        evidenceId="EV-FICT-B",
    )
    connection.close()
    connection = relate.connect(path, read_only=True)
    with pytest.raises(ValueError, match="exactly one offer or pool"):
        read_inventory(connection, "CAM-POE")
    connection.close()
    connection = relate.connect(path)
    connection.execute("MATCH (s:STOCK_OBSERVATION {id:'STOCK-FICT-B'}) REMOVE s.poolId")
    connection.close()
    connection = relate.connect(path, read_only=True)
    with pytest.raises(ValueError, match="multiple stock observations"):
        read_inventory(connection, "CAM-POE")
    connection.close()


def test_offer_hold_requires_matching_scope_and_exclusive_expiry() -> None:
    confirmed = StockClaim(
        "OFF-CONFIRMED",
        "SUP-FICT-A",
        None,
        StockState.SUPPLIER_CONFIRMED,
        2,
        NOW,
        NOW + timedelta(days=1),
        "confirmación ficticia",
        "EV-CONFIRMED",
    )
    hold = StockClaim(
        "OFF-HELD",
        "SUP-FICT-B",
        None,
        StockState.RESERVED,
        2,
        NOW,
        NOW + timedelta(days=1),
        "reserva ficticia",
        "EV-HOLD",
        reservation_id="HOLD-FICT-1",
        reservation_project_id=SCOPE.project_id,
        reservation_quote_id=SCOPE.quote_id,
        reservation_expires_at=NOW + timedelta(hours=1),
    )
    valid = evaluate_inventory(4, (confirmed, hold), (), (), now=NOW, scope=SCOPE)
    assert (valid.confirmed_quantity, valid.coverage, valid.shortage, valid.risk) == (
        4,
        1.0,
        0,
        RiskLevel.LOW,
    )
    cases = (
        (hold, None, NOW, "UNVERIFIED_RESERVATION"),
        (replace(hold, reservation_id=None), SCOPE, NOW, "UNVERIFIED_RESERVATION"),
        (replace(hold, evidence_id=None), SCOPE, NOW, "UNSOURCED_RESERVATION"),
        (replace(hold, reservation_quote_id=None), SCOPE, NOW, "UNVERIFIED_RESERVATION"),
        (
            replace(hold, reservation_quote_id="QUOTE-FICT-OTHER"),
            SCOPE,
            NOW,
            "RESERVATION_SCOPE_MISMATCH",
        ),
        (
            replace(hold, reservation_project_id="PROJECT-FICT-OTHER"),
            SCOPE,
            NOW,
            "RESERVATION_SCOPE_MISMATCH",
        ),
        (replace(hold, reservation_expires_at=None), SCOPE, NOW, "UNVERIFIED_RESERVATION"),
        (hold, SCOPE, NOW + timedelta(hours=1), "EXPIRED_RESERVATION"),
        (
            replace(hold, valid_until=NOW + timedelta(minutes=30)),
            SCOPE,
            NOW + timedelta(minutes=30),
            "STALE_STOCK",
        ),
    )
    for candidate, scope, at, reason in cases:
        result = evaluate_inventory(4, (confirmed, candidate), (), (), now=at, scope=scope)
        assert result.risk == RiskLevel.UNKNOWN
        assert (result.confirmed_quantity, result.coverage, result.shortage) == (None, None, None)
        assert result.claims[0].usable_confirmed_quantity == 2
        assert result.claims[1].usable_confirmed_quantity is None
        assert result.claims[1].reason == reason
        if reason != "UNSOURCED_RESERVATION":
            assert result.claims[1].claim.evidence_id == "EV-HOLD"


def test_one_hold_referenced_by_two_offers_is_counted_once() -> None:
    hold = StockClaim(
        "OFF-HELD-A",
        "SUP-FICT",
        None,
        StockState.RESERVED,
        2,
        NOW,
        NOW + timedelta(days=1),
        "reserva ficticia",
        "EV-HOLD",
        reservation_id="HOLD-FICT-1",
        reservation_project_id=SCOPE.project_id,
        reservation_quote_id=SCOPE.quote_id,
        reservation_expires_at=NOW + timedelta(hours=1),
    )
    result = evaluate_inventory(
        4, (hold, replace(hold, offer_id="OFF-HELD-B")), (), (), now=NOW, scope=SCOPE
    )
    assert (result.confirmed_quantity, result.coverage, result.shortage) == (2, 0.5, 2)
    assert result.claims[1].reason == "DUPLICATE_RESERVATION"
    assert result.claims[1].usable_confirmed_quantity is None


def test_one_hold_cannot_back_a_pool_cap_and_an_unpooled_offer() -> None:
    confirmed_pool_offer = StockClaim(
        "OFF-POOL-FICT",
        "SUP-POOL-FICT",
        None,
        StockState.SUPPLIER_CONFIRMED,
        2,
        NOW,
        NOW + timedelta(days=1),
        "confirmación ficticia",
        "EV-POOL-OFFER-FICT",
        "POOL-FICT",
    )
    held_other_offer = StockClaim(
        "OFF-OTHER-FICT",
        "SUP-OTHER-FICT",
        None,
        StockState.RESERVED,
        2,
        NOW,
        NOW + timedelta(days=1),
        "reserva ficticia",
        "EV-OTHER-HOLD-FICT",
        reservation_id="HOLD-FICT-SHARED",
        reservation_project_id=SCOPE.project_id,
        reservation_quote_id=SCOPE.quote_id,
        reservation_expires_at=NOW + timedelta(hours=1),
    )
    held_pool = PoolClaim(
        "POOL-FICT",
        StockState.RESERVED,
        2,
        NOW,
        NOW + timedelta(days=1),
        "reserva ficticia pool",
        "EV-POOL-HOLD-FICT",
        reservation_id="HOLD-FICT-SHARED",
        reservation_project_id=SCOPE.project_id,
        reservation_quote_id=SCOPE.quote_id,
        reservation_expires_at=NOW + timedelta(hours=1),
    )
    conflict = evaluate_inventory(
        4, (confirmed_pool_offer, held_other_offer), (held_pool,), (), now=NOW, scope=SCOPE
    )
    assert (conflict.confirmed_quantity, conflict.coverage, conflict.shortage) == (
        None,
        None,
        None,
    )
    assert conflict.risk == RiskLevel.UNKNOWN
    assert conflict.claims[0].usable_confirmed_quantity == 2
    assert conflict.claims[1].reason == "CONFLICTING_RESERVATION"
    assert "CONFLICTING_RESERVATION" in conflict.reasons
    same_pool_hold = replace(held_other_offer, pool_id="POOL-FICT", offer_id="OFF-SAME-POOL-FICT")
    same_pool = evaluate_inventory(
        4, (confirmed_pool_offer, same_pool_hold), (held_pool,), (), now=NOW, scope=SCOPE
    )
    assert (same_pool.confirmed_quantity, same_pool.coverage, same_pool.shortage) == (2, 0.5, 2)


def test_one_hold_cannot_cap_two_different_pools() -> None:
    first = StockClaim(
        "OFF-POOL-A",
        "SUP-FICT-A",
        None,
        StockState.SUPPLIER_CONFIRMED,
        2,
        NOW,
        NOW + timedelta(days=1),
        "confirmación ficticia",
        "EV-FICT-A",
        "POOL-A",
    )
    second = replace(first, offer_id="OFF-POOL-B", pool_id="POOL-B", evidence_id="EV-FICT-B")
    cap = PoolClaim(
        "POOL-A",
        StockState.RESERVED,
        2,
        NOW,
        NOW + timedelta(days=1),
        "reserva ficticia pool",
        "EV-CAP-A",
        reservation_id="HOLD-FICT-SHARED",
        reservation_project_id=SCOPE.project_id,
        reservation_quote_id=SCOPE.quote_id,
        reservation_expires_at=NOW + timedelta(hours=1),
    )
    result = evaluate_inventory(
        4,
        (first, second),
        (cap, replace(cap, pool_id="POOL-B", evidence_id="EV-CAP-B")),
        (),
        now=NOW,
        scope=SCOPE,
    )
    assert result.risk == RiskLevel.UNKNOWN
    assert (result.confirmed_quantity, result.coverage, result.shortage) == (None, None, None)
    assert "CONFLICTING_RESERVATION" in result.reasons


def test_graph_offer_and_pool_holds_require_quote_scope(tmp_path: Path) -> None:
    path = str(tmp_path / "held.db")
    connection = relate.connect(path)
    _seed(connection)
    _confirmed_graph(connection)
    for stock_id, hold_id, expiry in (
        ("STOCK-OFF-CAM-A", "HOLD-FICT-OFFER", "2026-11-26T14:00:00Z"),
        ("STOCK-POOL", "HOLD-FICT-POOL", "2026-11-26T13:00:00Z"),
    ):
        connection.execute(
            f"MATCH (s:STOCK_OBSERVATION {{id:'{stock_id}'}}) "
            "SET s.state = 'reserved', "
            f"s.reservationId = '{hold_id}', "
            "s.reservationProjectId = 'PROJECT-FICT-1', "
            "s.reservationQuoteId = 'QUOTE-FICT-1', "
            f"s.reservationExpiresAt = '{expiry}'"
        )
    connection.close()
    connection = relate.connect(path, read_only=True)
    snapshot = read_inventory(connection, "CAM-POE")
    held = evaluate_inventory(4, *snapshot, now=NOW, scope=SCOPE)
    assert (held.confirmed_quantity, held.coverage, held.shortage) == (2, 0.5, 2)
    assert held.claims[0].reason == "RESERVED"
    assert held.claims[1].reason == "CONFIRMED"
    wrong_offer = evaluate_inventory(
        4,
        (replace(snapshot[0][0], reservation_quote_id="QUOTE-FICT-OTHER"), snapshot[0][1]),
        snapshot[1],
        snapshot[2],
        now=NOW,
        scope=SCOPE,
    )
    assert wrong_offer.risk == RiskLevel.UNKNOWN
    assert "RESERVATION_SCOPE_MISMATCH" in wrong_offer.reasons
    wrong_pool = evaluate_inventory(
        4,
        snapshot[0],
        (replace(snapshot[1][0], reservation_quote_id="QUOTE-FICT-OTHER"),),
        snapshot[2],
        now=NOW,
        scope=SCOPE,
    )
    assert wrong_pool.risk == RiskLevel.UNKNOWN
    assert "POOL_RESERVATION_SCOPE_MISMATCH" in wrong_pool.reasons
    no_pool_reference = evaluate_inventory(
        4,
        snapshot[0],
        (replace(snapshot[1][0], reservation_quote_id=None),),
        snapshot[2],
        now=NOW,
        scope=SCOPE,
    )
    assert "POOL_UNVERIFIED_RESERVATION" in no_pool_reference.reasons
    at_pool_expiry = evaluate_inventory(4, *snapshot, now=NOW + timedelta(hours=1), scope=SCOPE)
    assert at_pool_expiry.risk == RiskLevel.UNKNOWN
    assert (at_pool_expiry.confirmed_quantity, at_pool_expiry.shortage) == (None, None)
    assert "POOL_EXPIRED_RESERVATION" in at_pool_expiry.reasons
    connection.close()
