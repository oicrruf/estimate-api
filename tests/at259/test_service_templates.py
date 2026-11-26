"""AT-259 service planning with fictitious scope and explicit price policy."""

from dataclasses import asdict, replace
from decimal import Decimal
from typing import TypeVar

import pytest

from estimate_api.domain.scope_capture import (
    AssetAvailability,
    AssetValidation,
    Certainty,
    ClientAsset,
    Fact,
    Measurement,
    ScopeIntake,
    SupplyItem,
    SupplyOwner,
)
from estimate_api.pricing import (
    CurrencyPolicy,
    Money,
    PriceBasis,
    PriceStatus,
    TaxPolicy,
    TaxTreatment,
)
from estimate_api.services import (
    ClientAssetAllocation,
    Complexity,
    ContingencyDecision,
    ExistingWork,
    ExistingWorkStatus,
    MaterialRequirement,
    MaterialUse,
    ServicePricePolicy,
    ServiceRequest,
    ServiceStatus,
    ServiceTemplate,
    VerificationStep,
    evaluate_service,
)

USD = CurrencyPolicy("USD", 2)
TAX = TaxPolicy(TaxTreatment.EXCLUDED, Decimal("0.13"), "RULE-FICT")
T = TypeVar("T")


def _confirmed(value: T) -> Fact[T]:
    return Fact(value, Certainty.CONFIRMED, "CLIENT-FICT")


def _scope(
    *,
    assets: tuple[ClientAsset, ...] = (),
    supplies: tuple[SupplyItem, ...] = (),
) -> ScopeIntake:
    return ScopeIntake(
        "Fictitious installation",
        objective=_confirmed("Install and verify the fixture"),
        location=_confirmed("Sample room"),
        environment=_confirmed("Indoor, accessible"),
        sketch=_confirmed("SKETCH-FICT"),
        measurements=_confirmed((Measurement("clearance", 2.0, "m"),)),
        restrictions=_confirmed(()),
        exclusions=_confirmed(("Wall repair",)),
        client_assets=assets,
        supplies=supplies,
        client_assets_absence_evidence=None if assets else "CLIENT-NO-ASSETS-FICT",
        supplies_absence_evidence=None if supplies else "CLIENT-NO-SUPPLIES-FICT",
    )


def _template(*materials: MaterialRequirement, labor_units: int = 1) -> ServiceTemplate:
    return ServiceTemplate(
        "SERVICE-FICT",
        "Fixture installation",
        Complexity.MEDIUM,
        ("Mount fixture", "Check operation"),
        ("Wall repair",),
        materials,
        (VerificationStep("TEST-FICT", "Verify fixture operation"),),
        labor_units,
    )


def _policy(
    *,
    contingency: ContingencyDecision = ContingencyDecision.APPLIES,
    tax: TaxPolicy = TAX,
    basis: PriceBasis = PriceBasis.NET,
) -> ServicePricePolicy:
    return ServicePricePolicy(Money(Decimal("40.00"), USD), basis, tax, "PRICE-FICT", contingency)


def _request(
    *,
    template: ServiceTemplate | None = None,
    scope: ScopeIntake | None = None,
    policy: ServicePricePolicy | None = None,
    allocations: tuple[ClientAssetAllocation, ...] = (),
) -> ServiceRequest:
    return ServiceRequest(
        template or _template(),
        scope or _scope(),
        policy or _policy(),
        existing_work_absence_evidence="CLIENT-NO-EXISTING-WORK-FICT",
        client_asset_allocations=allocations,
    )


def test_stipulated_labor_case_uses_pricing_once_and_hides_internal_components() -> None:
    result = evaluate_service(_request())
    assert result.projection.status == ServiceStatus.READY
    assert result.projection.total == Decimal("47.46")
    assert result.projection.currency_code == "USD"
    assert result.projection.excluded_work == ("Wall repair",)
    assert result.projection.verification_steps[0].step_id == "TEST-FICT"
    assert result.internal_pricing is not None
    assert result.internal_pricing.lines[0].contingency_unit == Decimal("2.0000")
    assert result.internal_pricing.lines[0].tax_added_unit == Decimal("5.460000")
    assert result.internal_pricing.lines[0].rounded_unit == Decimal("47.46")
    assert "contingency" not in str(asdict(result.projection)).lower()
    three = evaluate_service(_request(template=_template(labor_units=3)))
    assert three.projection.total == Decimal("142.38")


def test_contingency_is_only_applied_when_explicitly_applicable() -> None:
    no_contingency = evaluate_service(
        _request(policy=_policy(contingency=ContingencyDecision.NOT_APPLICABLE))
    )
    assert no_contingency.projection.total == Decimal("45.20")
    assert no_contingency.internal_pricing is not None
    assert no_contingency.internal_pricing.lines[0].contingency_unit == Decimal(0)
    unknown = evaluate_service(_request(policy=_policy(contingency=ContingencyDecision.UNKNOWN)))
    assert unknown.internal_pricing is None
    assert unknown.projection.total is None
    assert unknown.internal_pending_fields == ("pricing.contingency_applicability",)
    assert unknown.projection.pending_fields == ("pricing.confirmation",)
    assert "contingency" not in str(asdict(unknown.projection)).lower()


def test_validated_client_asset_is_never_a_purchase_and_quantity_is_evidenced() -> None:
    cabinet = ClientAsset(
        "Cabinet", AssetAvailability.AVAILABLE, AssetValidation.VALIDATED, "CHECK-FICT"
    )
    reused = MaterialRequirement("Cabinet", 2, "unit", MaterialUse.CLIENT_ASSET)
    excluded = MaterialRequirement("Paint", 1, "unit", MaterialUse.EXCLUDED)
    result = evaluate_service(
        _request(
            template=_template(reused, excluded),
            scope=_scope(assets=(cabinet,)),
            allocations=(ClientAssetAllocation("Cabinet", 2, "COUNT-FICT"),),
        )
    )
    assert result.projection.status == ServiceStatus.READY
    assert result.projection.purchase_items == ()
    assert result.projection.client_assets == (reused,)
    assert result.projection.excluded_materials == (excluded,)
    assert result.scope_draft.purchase_items == ()


@pytest.mark.parametrize(
    ("asset", "allocations", "expected"),
    [
        (None, (), "validated_client_asset"),
        (
            ClientAsset("Cabinet", AssetAvailability.UNKNOWN, AssetValidation.UNKNOWN),
            (ClientAssetAllocation("Cabinet", 2, "COUNT-FICT"),),
            "validated_client_asset",
        ),
        (
            ClientAsset(
                "Cabinet", AssetAvailability.AVAILABLE, AssetValidation.VALIDATED, "CHECK-FICT"
            ),
            (),
            "verified_quantity",
        ),
        (
            ClientAsset(
                "Cabinet", AssetAvailability.AVAILABLE, AssetValidation.VALIDATED, "CHECK-FICT"
            ),
            (ClientAssetAllocation("Cabinet", 1, "COUNT-FICT"),),
            "verified_quantity",
        ),
    ],
)
def test_missing_asset_evidence_stays_pending_without_purchase(
    asset: ClientAsset | None,
    allocations: tuple[ClientAssetAllocation, ...],
    expected: str,
) -> None:
    material = MaterialRequirement("Cabinet", 2, "unit", MaterialUse.CLIENT_ASSET)
    result = evaluate_service(
        _request(
            template=_template(material),
            scope=_scope(assets=(asset,) if asset is not None else ()),
            allocations=allocations,
        )
    )
    assert result.projection.status == ServiceStatus.PENDING
    assert result.projection.total is None
    assert result.projection.purchase_items == ()
    assert f"materials.Cabinet.{expected}" in result.projection.pending_fields


def test_purchase_conflict_with_client_ownership_fails_closed() -> None:
    required = MaterialRequirement("Cabinet", 1, "unit", MaterialUse.PURCHASE)
    cabinet = ClientAsset(
        "Cabinet", AssetAvailability.AVAILABLE, AssetValidation.VALIDATED, "CHECK-FICT"
    )
    result = evaluate_service(
        _request(template=_template(required), scope=_scope(assets=(cabinet,)))
    )
    assert result.projection.purchase_items == ()
    assert result.projection.total is None
    assert "materials.Cabinet.ownership" in result.projection.pending_fields
    client_supply = SupplyItem("Cabinet", SupplyOwner.CLIENT)
    result = evaluate_service(
        _request(template=_template(required), scope=_scope(supplies=(client_supply,)))
    )
    assert result.projection.purchase_items == ()
    assert "materials.Cabinet.ownership" in result.projection.pending_fields


def test_unpriced_purchase_remains_visible_and_blocks_final_total() -> None:
    required = MaterialRequirement("Bracket", 2, "unit", MaterialUse.PURCHASE)
    result = evaluate_service(_request(template=_template(required)))
    assert result.projection.purchase_items == (required,)
    assert result.projection.total is None
    assert result.projection.pending_fields == ("materials.Bracket.price",)
    assert result.internal_pricing is not None
    assert result.internal_pricing.status == PriceStatus.PRICED


def test_unknown_scope_existing_work_or_tax_remains_pending() -> None:
    unknown_scope = ScopeIntake("Install fixture")
    result = evaluate_service(_request(scope=unknown_scope))
    assert result.projection.status == ServiceStatus.PENDING
    assert result.projection.total is None
    assert "scope.objective" in result.projection.pending_fields
    unknown_work = ExistingWork("Old conduit", ExistingWorkStatus.UNKNOWN)
    result = evaluate_service(
        replace(_request(), existing_work=(unknown_work,), existing_work_absence_evidence=None)
    )
    assert "existing_work.Old conduit" in result.projection.pending_fields
    missing_tax = TaxPolicy(TaxTreatment.EXCLUDED, None, "RULE-FICT-PENDING")
    result = evaluate_service(_request(policy=_policy(tax=missing_tax)))
    assert result.projection.total is None
    assert "pricing.tax_rate" in result.projection.pending_fields


def test_verified_existing_work_is_retained_without_invented_repair() -> None:
    existing = ExistingWork("Old conduit", ExistingWorkStatus.VERIFIED, "CHECK-FICT-OLD")
    result = evaluate_service(
        replace(_request(), existing_work=(existing,), existing_work_absence_evidence=None)
    )
    assert result.projection.status == ServiceStatus.READY
    assert result.projection.existing_work == (existing,)
    assert result.projection.purchase_items == ()


def test_reject_invalid_templates_allocations_and_policy() -> None:
    with pytest.raises(ValueError, match="both included and excluded"):
        replace(_template(), excluded_work=("Mount fixture",))
    with pytest.raises(ValueError, match="duplicate names"):
        _template(
            MaterialRequirement("Cabinet", 1, "unit", MaterialUse.PURCHASE),
            MaterialRequirement(" cabinet ", 1, "unit", MaterialUse.EXCLUDED),
        )
    with pytest.raises(ValueError, match="positive bounded"):
        MaterialRequirement("Cabinet", True, "unit", MaterialUse.CLIENT_ASSET)
    with pytest.raises(ValueError, match="contingency"):
        _policy(basis=PriceBasis.CONFIRMED_FINAL)
    with pytest.raises(ValueError, match="evidence"):
        ExistingWork("Old conduit", ExistingWorkStatus.VERIFIED)
    with pytest.raises(ValueError, match="reusable material"):
        replace(
            _request(),
            client_asset_allocations=(ClientAssetAllocation("Cabinet", 1, "COUNT-FICT"),),
        )
    with pytest.raises(ValueError, match="absence evidence"):
        replace(
            _request(),
            existing_work=(ExistingWork("Old conduit", ExistingWorkStatus.UNKNOWN),),
        )
    with pytest.raises(ValueError, match="unique"):
        replace(
            _request(),
            existing_work=(
                ExistingWork("Old conduit", ExistingWorkStatus.UNKNOWN),
                ExistingWork(" old conduit ", ExistingWorkStatus.UNKNOWN),
            ),
            existing_work_absence_evidence=None,
        )
