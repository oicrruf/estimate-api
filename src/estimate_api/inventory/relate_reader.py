"""Read AT-229 offers and optional AT-233 synthetic claims from Relate.

The supplied connection is never written to. Stock observations are separate
from technical capabilities and from the AT-229 public offer quantities.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from estimate_api.inventory.risk import Dependency, PoolClaim, StockClaim, StockState


def _date(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("stock evidence date must include timezone")
    return parsed


def read_inventory(
    connection: Any, product_id: str
) -> tuple[tuple[StockClaim, ...], tuple[PoolClaim, ...], tuple[Dependency, ...]]:
    """Return one neutral snapshot for a product; no eligibility or selection."""
    # Filter in Python to avoid constructing Cypher from caller-controlled IDs.
    offers = [
        row
        for row in connection.execute(
            "MATCH (o:OFFER)-[:SELLS]->(p:PRODUCT) "
            "RETURN o.id AS offerId,p.id AS productId,o.seller AS supplierId, "
            "o.quantity AS publishedQuantity,o.poolId AS poolId"
        ).data()
        if row["productId"] == product_id
    ]
    offer_ids = {row["offerId"] for row in offers}
    observation_rows = connection.execute(
        "MATCH (s:STOCK_OBSERVATION) "
        "OPTIONAL MATCH (s)-[:SUPPORTED_BY]->(e:EVIDENCE) "
        "RETURN s.offerId AS offerId,s.poolId AS poolId, "
        "s.state AS state,s.quantity AS quantity,s.observedAt AS observedAt, "
        "s.validUntil AS validUntil,s.supplierId AS supplierId,s.branchId AS branchId, "
        "s.restockAt AS restockAt,e.source AS source,e.id AS evidenceId"
    ).data()
    observed_keys = [(row["offerId"], row["poolId"]) for row in observation_rows]
    if len(observed_keys) != len(set(observed_keys)):
        raise ValueError("multiple stock observations or evidence links for one subject")
    by_offer = {row["offerId"]: row for row in observation_rows if row["offerId"] in offer_ids}
    claims: list[StockClaim] = []
    for offer in offers:
        row = by_offer.get(offer["offerId"])
        if row is None:
            claims.append(
                StockClaim(
                    offer["offerId"],
                    offer["supplierId"],
                    None,
                    StockState.PUBLISHED,
                    offer["publishedQuantity"],
                    None,
                    None,
                    "AT-229 synthetic offer",
                    None,
                    offer["poolId"],
                )
            )
        else:
            if row["supplierId"] and row["supplierId"] != offer["supplierId"]:
                raise ValueError("stock claim supplier differs from offer seller")
            claims.append(
                StockClaim(
                    offer["offerId"],
                    row["supplierId"] or offer["supplierId"],
                    row["branchId"],
                    StockState(row["state"]),
                    row["quantity"],
                    _date(row["observedAt"]),
                    _date(row["validUntil"]),
                    row["source"],
                    row["evidenceId"],
                    offer["poolId"],
                    _date(row["restockAt"]),
                )
            )
    pool_ids = {row["poolId"] for row in offers if row["poolId"]}
    pool_rows = connection.execute(
        "MATCH (p:PRODUCT)-[:SUPPORTS]->(c:CAPABILITY {key:'poolCapacity'})"
        "-[:SUPPORTED_BY]->(e:EVIDENCE) RETURN p.id AS productId,p.poolId AS poolId, "
        "c.value AS quantity,e.id AS evidenceId,e.source AS source"
    ).data()
    by_pool = {
        row["poolId"]: row
        for row in observation_rows
        if row["poolId"] in pool_ids and row["offerId"] is None
    }
    caps: list[PoolClaim] = []
    for pool_id in sorted(pool_ids):
        row = by_pool.get(pool_id)
        legacy = next(
            (r for r in pool_rows if r["poolId"] == pool_id and r["productId"] == product_id), None
        )
        if row is not None:
            caps.append(
                PoolClaim(
                    pool_id,
                    StockState(row["state"]),
                    row["quantity"],
                    _date(row["observedAt"]),
                    _date(row["validUntil"]),
                    row["source"],
                    row["evidenceId"],
                )
            )
        elif legacy is not None:
            caps.append(
                PoolClaim(
                    pool_id,
                    StockState.PUBLISHED,
                    legacy["quantity"],
                    None,
                    None,
                    legacy["source"],
                    legacy["evidenceId"],
                )
            )
    dependencies: list[Dependency] = []
    for pool_id in sorted(pool_ids):
        legacy = next(
            (r for r in pool_rows if r["poolId"] == pool_id and r["productId"] == product_id), None
        )
        members = sorted(row["offerId"] for row in offers if row["poolId"] == pool_id)
        if legacy and legacy["evidenceId"] and legacy["source"]:
            for left_index, left in enumerate(members):
                for right in members[left_index + 1 :]:
                    dependencies.append(
                        Dependency(
                            left,
                            right,
                            "shared_pool",
                            pool_id,
                            legacy["evidenceId"],
                            legacy["source"],
                        )
                    )
    distributors = connection.execute(
        "MATCH (o:OFFER)-[r:DISTRIBUTED_BY]->(d:DISTRIBUTOR) "
        "RETURN o.id AS offerId,d.id AS distributorId, "
        "r.evidenceId AS evidenceId,r.source AS source"
    ).data()
    evidence = {
        row["evidenceId"]: row["source"]
        for row in connection.execute(
            "MATCH (e:EVIDENCE) RETURN e.id AS evidenceId,e.source AS source"
        ).data()
    }
    by_distributor: dict[str, list[dict[str, Any]]] = {}
    for row in distributors:
        if row["offerId"] in offer_ids and evidence.get(row["evidenceId"]):
            row["source"] = evidence[row["evidenceId"]]
            by_distributor.setdefault(row["distributorId"], []).append(row)
    for distributor_id, members in sorted(by_distributor.items()):
        members.sort(key=lambda row: row["offerId"])
        for left_index, left in enumerate(members):
            for right in members[left_index + 1 :]:
                dependencies.append(
                    Dependency(
                        left["offerId"],
                        right["offerId"],
                        "shared_distributor",
                        distributor_id,
                        f"{left['evidenceId']}+{right['evidenceId']}",
                        f"{left['source']} | {right['source']}",
                    )
                )
    return tuple(claims), tuple(caps), tuple(dependencies)
