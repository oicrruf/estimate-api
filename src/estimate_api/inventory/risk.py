"""Neutral inventory contract and commercial-risk evaluation.

No technical eligibility, price ranking, supplier contact, or reservation is performed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Literal


class StockState(StrEnum):
    UNKNOWN = "unknown"
    PUBLISHED = "published"
    SUPPLIER_CONFIRMED = "supplier_confirmed"
    RESERVED = "reserved"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class StockClaim:
    offer_id: str
    supplier_id: str
    branch_id: str | None
    state: StockState
    quantity: int | None
    observed_at: datetime | None
    valid_until: datetime | None
    source: str | None
    evidence_id: str | None
    pool_id: str | None = None
    restock_at: datetime | None = None


@dataclass(frozen=True)
class PoolClaim:
    pool_id: str
    state: StockState
    quantity: int | None
    observed_at: datetime | None
    valid_until: datetime | None
    source: str | None
    evidence_id: str | None


@dataclass(frozen=True)
class Dependency:
    left_offer_id: str
    right_offer_id: str
    kind: Literal["shared_pool", "shared_distributor"]
    identifier: str
    evidence_id: str
    source: str


@dataclass(frozen=True)
class RiskThresholds:
    medium_coverage: float = 1.0
    high_coverage: float = 0.5

    def __post_init__(self) -> None:
        if not 0 <= self.high_coverage < self.medium_coverage <= 1:
            raise ValueError("coverage thresholds must satisfy 0 <= high < medium <= 1")


@dataclass(frozen=True)
class ClaimAssessment:
    claim: StockClaim
    stale: bool
    usable_confirmed_quantity: int | None
    reason: str


@dataclass(frozen=True)
class InventoryAssessment:
    requested_quantity: int
    confirmed_quantity: int | None
    coverage: float | None
    shortage: int | None
    risk: RiskLevel
    reasons: tuple[str, ...]
    claims: tuple[ClaimAssessment, ...]
    dependencies: tuple[Dependency, ...]
    pool_caps: tuple[PoolClaim, ...]
    alternative_review_required: bool
    technical_eligibility: None = None
    recommendation_score: None = None
    manual_selection: None = None


def _check_quantity(quantity: int | None) -> None:
    if quantity is not None and (
        isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 0
    ):
        raise ValueError("quantity must be a nonnegative integer or unknown")


def _fresh(observed_at: datetime | None, valid_until: datetime | None, now: datetime) -> bool:
    return bool(
        observed_at
        and valid_until
        and observed_at.tzinfo
        and valid_until.tzinfo
        and observed_at <= now <= valid_until
    )


def evaluate_inventory(
    requested_quantity: int,
    claims: tuple[StockClaim, ...],
    pool_caps: tuple[PoolClaim, ...],
    dependencies: tuple[Dependency, ...],
    *,
    now: datetime,
    thresholds: RiskThresholds | None = None,
) -> InventoryAssessment:
    """Evaluate documented supply, preserving public and stale claims as evidence only.

    One current claim per offer and pool is required. Duplicate or conflicting pool
    evidence fails closed rather than adding quantities from the same physical stock.
    """
    if (
        isinstance(requested_quantity, bool)
        or not isinstance(requested_quantity, int)
        or requested_quantity <= 0
    ):
        raise ValueError("requested_quantity must be positive")
    if now.tzinfo is None:
        raise ValueError("now must be timezone aware")
    thresholds = thresholds or RiskThresholds()
    offer_ids = [claim.offer_id for claim in claims]
    if len(offer_ids) != len(set(offer_ids)):
        raise ValueError("multiple current claims for one offer")
    pool_ids = [pool.pool_id for pool in pool_caps]
    if len(pool_ids) != len(set(pool_ids)):
        raise ValueError("multiple current claims for one pool")
    pools = {pool.pool_id: pool for pool in pool_caps}
    for pool_claim in pool_caps:
        _check_quantity(pool_claim.quantity)
    assessed: list[ClaimAssessment] = []
    unpooled_total = 0
    pooled: dict[str, int] = {}
    reasons: set[str] = set()
    unresolved = False
    for claim in claims:
        _check_quantity(claim.quantity)
        if not isinstance(claim.state, StockState):
            raise ValueError("unknown stock state")
        stale = claim.state != StockState.UNKNOWN and not _fresh(
            claim.observed_at, claim.valid_until, now
        )
        if claim.state == StockState.UNKNOWN or claim.quantity is None:
            reason = "UNKNOWN_STOCK"
        elif claim.state == StockState.PUBLISHED:
            reason = "PUBLIC_ONLY"
        elif stale:
            reason = "STALE_STOCK"
        elif not claim.source or not claim.evidence_id:
            reason = "UNSOURCED_CONFIRMATION"
        else:
            reason = "CONFIRMED" if claim.state == StockState.SUPPLIER_CONFIRMED else "RESERVED"
        usable = claim.quantity if reason in ("CONFIRMED", "RESERVED") else None
        if usable is None:
            unresolved = True
            reasons.add(reason)
        elif claim.pool_id:
            pooled[claim.pool_id] = pooled.get(claim.pool_id, 0) + usable
        else:
            unpooled_total += usable
        assessed.append(ClaimAssessment(claim, stale, usable, reason))

    total = unpooled_total
    for pool_id, offer_total in pooled.items():
        pool = pools.get(pool_id)
        if (
            pool is None
            or pool.quantity is None
            or pool.state
            not in (
                StockState.SUPPLIER_CONFIRMED,
                StockState.RESERVED,
            )
            or not pool.source
            or not pool.evidence_id
            or not _fresh(pool.observed_at, pool.valid_until, now)
        ):
            unresolved = True
            reasons.add("UNVERIFIED_SHARED_POOL")
            continue
        total += min(offer_total, pool.quantity)
        reasons.add("SHARED_POOL_CAP")

    for dependency in dependencies:
        if dependency.kind not in ("shared_pool", "shared_distributor"):
            raise ValueError("unknown dependency kind")
        if not dependency.evidence_id or not dependency.source:
            raise ValueError("dependency requires evidence and source")
        if dependency.left_offer_id not in offer_ids or dependency.right_offer_id not in offer_ids:
            raise ValueError("dependency references unknown offer")
        reasons.add("SHARED_POOL" if dependency.kind == "shared_pool" else "SHARED_DISTRIBUTOR")

    if not claims or unresolved:
        risk = RiskLevel.UNKNOWN
        coverage = None
        shortage = None
        confirmed = None
        reasons.add("INSUFFICIENT_CONFIRMATION")
    else:
        confirmed = total
        coverage = min(total / requested_quantity, 1.0)
        shortage = max(requested_quantity - total, 0)
        if coverage <= thresholds.high_coverage:
            risk = RiskLevel.HIGH
        elif coverage < thresholds.medium_coverage:
            risk = RiskLevel.MEDIUM
        else:
            risk = RiskLevel.LOW
        if shortage:
            reasons.add("CONFIRMED_SHORTAGE")
    return InventoryAssessment(
        requested_quantity,
        confirmed,
        coverage,
        shortage,
        risk,
        tuple(sorted(reasons)),
        tuple(assessed),
        dependencies,
        pool_caps,
        risk != RiskLevel.LOW,
    )
