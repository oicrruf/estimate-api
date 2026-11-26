"""Pure service planning; no procurement, tax discovery, or persistence."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from estimate_api.domain.scope_capture import (
    AssetAvailability,
    AssetValidation,
    ScopeDraft,
    ScopeIntake,
    SupplyOwner,
    build_scope_draft,
)
from estimate_api.pricing import (
    LineKind,
    Money,
    PriceBasis,
    PricedQuote,
    PriceLine,
    PriceStatus,
    QuoteInput,
    TaxPolicy,
    price_quote,
)

CONTRACT_VERSION = "at259.service-template.v1"
INTERNAL_CONTINGENCY_RATE = Decimal("0.05")
MAX_SERVICE_QUANTITY = 1_000_000_000


def _nonempty(value: object, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a nonempty string")


def _named_items(values: object, field: str, *, required: bool = False) -> None:
    if not isinstance(values, tuple) or (required and not values):
        raise ValueError(f"{field} must be a {'nonempty ' if required else ''}tuple")
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError(f"{field} must contain nonempty strings")
    if len({value.strip().casefold() for value in values}) != len(values):
        raise ValueError(f"{field} contains duplicate names")


def _merge_names(first: tuple[str, ...], second: tuple[str, ...]) -> tuple[str, ...]:
    names: list[str] = []
    seen: set[str] = set()
    for name in (*first, *second):
        key = name.strip().casefold()
        if key not in seen:
            names.append(name)
            seen.add(key)
    return tuple(names)


class Complexity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class MaterialUse(StrEnum):
    PURCHASE = "purchase"
    CLIENT_ASSET = "client_asset"
    EXCLUDED = "excluded"


class ContingencyDecision(StrEnum):
    APPLIES = "applies"
    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"


class ServiceStatus(StrEnum):
    READY = "ready"
    PENDING = "pending"


class ExistingWorkStatus(StrEnum):
    VERIFIED = "verified"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ExistingWork:
    description: str
    status: ExistingWorkStatus
    evidence: str | None = None

    def __post_init__(self) -> None:
        _nonempty(self.description, "existing work description")
        if not isinstance(self.status, ExistingWorkStatus):
            raise ValueError("existing work status must be explicit")
        if self.status == ExistingWorkStatus.VERIFIED:
            _nonempty(self.evidence, "existing work evidence")


@dataclass(frozen=True)
class ClientAssetAllocation:
    material_name: str
    verified_quantity: int
    evidence: str

    def __post_init__(self) -> None:
        _nonempty(self.material_name, "client asset material name")
        _nonempty(self.evidence, "client asset quantity evidence")
        if (
            isinstance(self.verified_quantity, bool)
            or not isinstance(self.verified_quantity, int)
            or not 1 <= self.verified_quantity <= MAX_SERVICE_QUANTITY
        ):
            raise ValueError("verified client asset quantity must be positive and bounded")


@dataclass(frozen=True)
class MaterialRequirement:
    name: str
    quantity: int
    unit: str
    use: MaterialUse

    def __post_init__(self) -> None:
        _nonempty(self.name, "material name")
        _nonempty(self.unit, "material unit")
        if not isinstance(self.use, MaterialUse):
            raise ValueError("material use must be explicit")
        if (
            isinstance(self.quantity, bool)
            or not isinstance(self.quantity, int)
            or not 1 <= self.quantity <= MAX_SERVICE_QUANTITY
        ):
            raise ValueError("material quantity must be a positive bounded integer")


@dataclass(frozen=True)
class VerificationStep:
    step_id: str
    instruction: str

    def __post_init__(self) -> None:
        _nonempty(self.step_id, "verification step ID")
        _nonempty(self.instruction, "verification instruction")


@dataclass(frozen=True)
class ServiceTemplate:
    template_id: str
    name: str
    complexity: Complexity
    included_work: tuple[str, ...]
    excluded_work: tuple[str, ...]
    materials: tuple[MaterialRequirement, ...]
    verification_steps: tuple[VerificationStep, ...]
    labor_units: int

    def __post_init__(self) -> None:
        _nonempty(self.template_id, "template ID")
        _nonempty(self.name, "service name")
        if not isinstance(self.complexity, Complexity):
            raise ValueError("complexity must be explicit")
        _named_items(self.included_work, "included work", required=True)
        _named_items(self.excluded_work, "excluded work")
        if {item.strip().casefold() for item in self.included_work} & {
            item.strip().casefold() for item in self.excluded_work
        }:
            raise ValueError("work cannot be both included and excluded")
        if not isinstance(self.materials, tuple) or not all(
            isinstance(item, MaterialRequirement) for item in self.materials
        ):
            raise ValueError("materials must be a tuple of MaterialRequirement")
        if len({item.name.strip().casefold() for item in self.materials}) != len(self.materials):
            raise ValueError("materials contain duplicate names")
        if (
            not isinstance(self.verification_steps, tuple)
            or not self.verification_steps
            or not all(isinstance(step, VerificationStep) for step in self.verification_steps)
        ):
            raise ValueError("verification steps must be a nonempty tuple")
        if len({step.step_id for step in self.verification_steps}) != len(self.verification_steps):
            raise ValueError("verification step IDs must be unique")
        if (
            isinstance(self.labor_units, bool)
            or not isinstance(self.labor_units, int)
            or not 1 <= self.labor_units <= MAX_SERVICE_QUANTITY
        ):
            raise ValueError("labor units must be a positive bounded integer")


@dataclass(frozen=True)
class ServicePricePolicy:
    labor_base: Money
    labor_basis: PriceBasis
    tax: TaxPolicy
    price_source_ref: str
    contingency: ContingencyDecision

    def __post_init__(self) -> None:
        if not isinstance(self.labor_base, Money) or not isinstance(self.tax, TaxPolicy):
            raise ValueError("labor base and tax policy are required")
        if not isinstance(self.labor_basis, PriceBasis):
            raise ValueError("labor basis must be explicit")
        if not isinstance(self.contingency, ContingencyDecision):
            raise ValueError("contingency decision must be explicit")
        _nonempty(self.price_source_ref, "price source")
        if (
            self.labor_basis == PriceBasis.CONFIRMED_FINAL
            and self.contingency == ContingencyDecision.APPLIES
        ):
            raise ValueError("confirmed final prices cannot receive contingency")


@dataclass(frozen=True)
class ServiceRequest:
    template: ServiceTemplate
    scope_intake: ScopeIntake
    price_policy: ServicePricePolicy
    existing_work: tuple[ExistingWork, ...] = ()
    existing_work_absence_evidence: str | None = None
    client_asset_allocations: tuple[ClientAssetAllocation, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.template, ServiceTemplate):
            raise ValueError("service template is required")
        if not isinstance(self.scope_intake, ScopeIntake):
            raise ValueError("AT-246 scope intake is required")
        if not isinstance(self.price_policy, ServicePricePolicy):
            raise ValueError("service price policy is required")
        if not isinstance(self.existing_work, tuple) or not all(
            isinstance(item, ExistingWork) for item in self.existing_work
        ):
            raise ValueError("existing work must be a tuple of ExistingWork")
        existing_names = [item.description.strip().casefold() for item in self.existing_work]
        if len(existing_names) != len(set(existing_names)):
            raise ValueError("existing work descriptions must be unique")
        if self.existing_work_absence_evidence is not None:
            if (
                self.existing_work
                or not isinstance(self.existing_work_absence_evidence, str)
                or not self.existing_work_absence_evidence.strip()
            ):
                raise ValueError("existing work absence evidence requires no existing work")
        if not isinstance(self.client_asset_allocations, tuple) or not all(
            isinstance(item, ClientAssetAllocation) for item in self.client_asset_allocations
        ):
            raise ValueError("client asset allocations must be a tuple")
        allocation_keys = [
            item.material_name.strip().casefold() for item in self.client_asset_allocations
        ]
        if len(allocation_keys) != len(set(allocation_keys)):
            raise ValueError("client asset allocations must be unique")
        reusable = {
            item.name.strip().casefold()
            for item in self.template.materials
            if item.use == MaterialUse.CLIENT_ASSET
        }
        if any(key not in reusable for key in allocation_keys):
            raise ValueError("client asset allocation does not match a reusable material")


@dataclass(frozen=True)
class CustomerServiceProjection:
    """Safe customer fields; intentionally omits internal contingency components."""

    contract_version: str
    template_id: str
    name: str
    complexity: Complexity
    included_work: tuple[str, ...]
    excluded_work: tuple[str, ...]
    purchase_items: tuple[MaterialRequirement, ...]
    client_assets: tuple[MaterialRequirement, ...]
    excluded_materials: tuple[MaterialRequirement, ...]
    verification_steps: tuple[VerificationStep, ...]
    existing_work: tuple[ExistingWork, ...]
    status: ServiceStatus
    currency_code: str
    total: Decimal | None
    pending_fields: tuple[str, ...]


@dataclass(frozen=True)
class ServiceEvaluation:
    scope_draft: ScopeDraft
    internal_pricing: PricedQuote | None
    internal_pending_fields: tuple[str, ...]
    projection: CustomerServiceProjection


def evaluate_service(request: ServiceRequest) -> ServiceEvaluation:
    """Resolve explicit material ownership, then reuse AT-224 for all arithmetic."""
    template = request.template
    scope = build_scope_draft(request.scope_intake)
    pending = [f"scope.{question.field}" for question in scope.blocking_questions]
    if not request.existing_work and request.existing_work_absence_evidence is None:
        pending.append("existing_work")
    pending.extend(
        f"existing_work.{item.description}"
        for item in request.existing_work
        if item.status == ExistingWorkStatus.UNKNOWN
    )
    scope_exclusions = scope.exclusions.value if scope.exclusions is not None else ()
    exclusion_keys = {item.strip().casefold() for item in scope_exclusions}
    excluded_work = _merge_names(template.excluded_work, scope_exclusions)
    included_work = tuple(
        item for item in template.included_work if item.strip().casefold() not in exclusion_keys
    )
    pending.extend(
        f"scope.exclusions.conflict.{item}"
        for item in template.included_work
        if item.strip().casefold() in exclusion_keys
    )
    assets = {asset.name.strip().casefold(): asset for asset in scope.client_assets}
    supplies = {item.name.strip().casefold(): item for item in scope.supplies}
    template_materials = {item.name.strip().casefold(): item for item in template.materials}
    for scope_supply in scope.supplies:
        if not scope_supply.purchase_required:
            continue
        matched = template_materials.get(scope_supply.name.strip().casefold())
        if matched is None:
            pending.append(f"supplies.{scope_supply.name}.unmatched_purchase")
        elif matched.use != MaterialUse.PURCHASE:
            pending.append(f"supplies.{scope_supply.name}.purchase_conflict")
    allocations = {
        item.material_name.strip().casefold(): item for item in request.client_asset_allocations
    }
    purchase_items: list[MaterialRequirement] = []
    client_assets: list[MaterialRequirement] = []
    excluded_materials: list[MaterialRequirement] = []
    for material in template.materials:
        key = material.name.strip().casefold()
        asset = assets.get(key)
        supply = supplies.get(key)
        field = f"materials.{material.name}"
        if material.use == MaterialUse.EXCLUDED:
            excluded_materials.append(material)
        elif material.use == MaterialUse.CLIENT_ASSET:
            client_assets.append(material)
            if asset is None or (
                asset.availability != AssetAvailability.AVAILABLE
                or asset.validation != AssetValidation.VALIDATED
            ):
                pending.append(f"{field}.validated_client_asset")
            allocation = allocations.get(key)
            if allocation is None or allocation.verified_quantity < material.quantity:
                pending.append(f"{field}.verified_quantity")
        elif asset is not None or (supply is not None and supply.supplied_by == SupplyOwner.CLIENT):
            # A client-owned item is never silently converted into a purchase.
            pending.append(f"{field}.ownership")
        elif supply is not None and not supply.purchase_required:
            pending.append(f"{field}.purchase_required")
        else:
            purchase_items.append(material)
            # AT-259 plans quantity and ownership; it does not invent a material price.
            pending.append(f"{field}.price")

    pricing: PricedQuote | None = None
    if request.price_policy.contingency == ContingencyDecision.UNKNOWN:
        pending.append("pricing.contingency_applicability")
    else:
        policy = request.price_policy
        line = PriceLine(
            f"{template.template_id}:labor",
            LineKind.LABOR,
            policy.labor_basis,
            policy.labor_base,
            template.labor_units,
            policy.tax,
            policy.price_source_ref,
            INTERNAL_CONTINGENCY_RATE
            if policy.contingency == ContingencyDecision.APPLIES
            else Decimal(0),
        )
        pricing = price_quote(QuoteInput(policy.labor_base.currency, (line,)))
        if pricing.status == PriceStatus.PENDING:
            pending.extend(f"pricing.{field}" for field in pricing.lines[0].missing_fields)

    pending_fields = tuple(dict.fromkeys(pending))
    status = ServiceStatus.PENDING if pending_fields else ServiceStatus.READY
    public_pending_fields = tuple(
        dict.fromkeys(
            "pricing.confirmation" if field == "pricing.contingency_applicability" else field
            for field in pending_fields
        )
    )
    projection = CustomerServiceProjection(
        CONTRACT_VERSION,
        template.template_id,
        template.name,
        template.complexity,
        included_work,
        excluded_work,
        tuple(purchase_items),
        tuple(client_assets),
        tuple(excluded_materials),
        template.verification_steps,
        request.existing_work,
        status,
        request.price_policy.labor_base.currency.code,
        pricing.total if status == ServiceStatus.READY and pricing is not None else None,
        public_pending_fields,
    )
    return ServiceEvaluation(scope, pricing, pending_fields, projection)
