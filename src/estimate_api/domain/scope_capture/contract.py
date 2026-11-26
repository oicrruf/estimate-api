"""Pure, typed scope draft construction. No persistence or service access."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Generic, TypeVar

CONTRACT_VERSION = "at246.scope-draft.v1"
T = TypeVar("T")


class Certainty(StrEnum):
    CONFIRMED = "confirmed"
    INFERRED = "inferred"


class SupplyOwner(StrEnum):
    CLIENT = "client"
    CONTRACTOR = "contractor"


class AssetAvailability(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class AssetValidation(StrEnum):
    VALIDATED = "validated"
    UNVALIDATED = "unvalidated"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Fact(Generic[T]):
    value: T
    certainty: Certainty
    evidence: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.certainty, Certainty):
            raise ValueError("certainty must be a Certainty value")
        if self.certainty == Certainty.CONFIRMED and not (self.evidence or "").strip():
            raise ValueError("confirmed facts require explicit evidence")


@dataclass(frozen=True)
class Measurement:
    label: str
    value: float
    unit: str

    def __post_init__(self) -> None:
        if not self.label.strip() or not self.unit.strip() or self.value <= 0:
            raise ValueError("measurement needs a label, positive value, and unit")


@dataclass(frozen=True)
class ClientAsset:
    name: str
    availability: AssetAvailability
    validation: AssetValidation
    evidence: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.availability, AssetAvailability) or not isinstance(
            self.validation, AssetValidation
        ):
            raise ValueError("asset availability and validation must use their enums")
        if not self.name.strip():
            raise ValueError("client asset name is required")
        if (
            self.validation == AssetValidation.VALIDATED
            and self.availability != AssetAvailability.AVAILABLE
        ):
            raise ValueError("only available client assets can be validated")
        if self.validation == AssetValidation.VALIDATED and not (self.evidence or "").strip():
            raise ValueError("validated client assets require evidence")

    @property
    def supplied_by(self) -> SupplyOwner:
        return SupplyOwner.CLIENT

    @property
    def purchase_required(self) -> bool:
        return False


@dataclass(frozen=True)
class SupplyItem:
    name: str
    supplied_by: SupplyOwner
    purchase_required: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.supplied_by, SupplyOwner):
            raise ValueError("supply owner must be a SupplyOwner value")
        if not self.name.strip():
            raise ValueError("supply item name is required")
        if self.supplied_by == SupplyOwner.CLIENT and self.purchase_required:
            raise ValueError("client-supplied items cannot be marked for purchase")


@dataclass(frozen=True)
class ScopeIntake:
    description: str
    objective: Fact[str] | None = None
    location: Fact[str] | None = None
    environment: Fact[str] | None = None
    sketch: Fact[str] | None = None
    measurements: Fact[tuple[Measurement, ...]] | None = None
    restrictions: Fact[tuple[str, ...]] | None = None
    exclusions: Fact[tuple[str, ...]] | None = None
    client_assets: tuple[ClientAsset, ...] = ()
    supplies: tuple[SupplyItem, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.client_assets, tuple) or not isinstance(self.supplies, tuple):
            raise ValueError("client_assets and supplies must be tuples")
        if not self.description.strip():
            raise ValueError("description is required")
        for name in ("objective", "location", "environment", "sketch"):
            fact = getattr(self, name)
            if fact is not None and not fact.value.strip():
                raise ValueError(f"{name} cannot be blank")
        if self.measurements is not None and not self.measurements.value:
            raise ValueError("measurements cannot be empty; use None when unknown")
        if self.measurements is not None and not isinstance(self.measurements.value, tuple):
            raise ValueError("measurements must be a tuple")
        for name in ("restrictions", "exclusions"):
            fact = getattr(self, name)
            if fact is not None and not isinstance(fact.value, tuple):
                raise ValueError(f"{name} must be a tuple")
            if fact is not None and any(not item.strip() for item in fact.value):
                raise ValueError(f"{name} cannot contain blank entries")
        asset_names = [asset.name.strip().casefold() for asset in self.client_assets]
        supply_names = [item.name.strip().casefold() for item in self.supplies]
        if len(asset_names + supply_names) != len(set(asset_names + supply_names)):
            raise ValueError("asset and supply names must be unique")


@dataclass(frozen=True)
class BlockingQuestion:
    field: str
    text: str


@dataclass(frozen=True)
class ScopeDraft:
    contract_version: str
    description: str
    objective: Fact[str] | None
    location: Fact[str] | None
    environment: Fact[str] | None
    sketch: Fact[str] | None
    measurements: Fact[tuple[Measurement, ...]] | None
    restrictions: Fact[tuple[str, ...]] | None
    exclusions: Fact[tuple[str, ...]] | None
    client_assets: tuple[ClientAsset, ...]
    supplies: tuple[SupplyItem, ...]
    blocking_questions: tuple[BlockingQuestion, ...]

    @property
    def purchase_items(self) -> tuple[str, ...]:
        return tuple(item.name for item in self.supplies if item.purchase_required)


_MISSING_QUESTIONS = (
    ("objective", "What work or outcome should this estimate cover?"),
    ("location", "What is the exact installation location or site area?"),
    ("environment", "Is the site indoors or outdoors, and what site conditions affect the work?"),
    ("sketch", "Can you provide a sketch or layout showing placement and connections?"),
    ("measurements", "What are the relevant dimensions, clearances, and units?"),
    (
        "restrictions",
        "What access, schedule, safety, or site restrictions apply? State none if there are none.",
    ),
    ("exclusions", "What work should be excluded? State none if there are no exclusions."),
)


def build_scope_draft(intake: ScopeIntake) -> ScopeDraft:
    """Preserve supplied facts and ask about missing or inferred details."""
    questions: list[BlockingQuestion] = []
    for field, prompt in _MISSING_QUESTIONS:
        fact = getattr(intake, field)
        if fact is None:
            questions.append(BlockingQuestion(field, prompt))
        elif fact.certainty == Certainty.INFERRED:
            questions.append(
                BlockingQuestion(field, f"Please confirm the inferred {field}: {fact.value}.")
            )
    if not intake.client_assets:
        questions.append(
            BlockingQuestion(
                "client_assets",
                "Which client-owned assets are available and validated? State none if applicable.",
            )
        )
    for asset in intake.client_assets:
        if asset.availability == AssetAvailability.UNKNOWN:
            questions.append(
                BlockingQuestion(
                    f"client_assets.{asset.name}.availability",
                    f"Is the client-supplied {asset.name} available on site?",
                )
            )
        if asset.validation != AssetValidation.VALIDATED:
            questions.append(
                BlockingQuestion(
                    f"client_assets.{asset.name}.validation",
                    f"Has client-supplied {asset.name} been checked for condition, dimensions, "
                    "and compatibility?",
                )
            )
    if not intake.supplies:
        questions.append(
            BlockingQuestion(
                "supplies",
                "Which items will the client supply and which will the contractor supply?",
            )
        )
    return ScopeDraft(
        contract_version=CONTRACT_VERSION,
        description=intake.description,
        objective=intake.objective,
        location=intake.location,
        environment=intake.environment,
        sketch=intake.sketch,
        measurements=intake.measurements,
        restrictions=intake.restrictions,
        exclusions=intake.exclusions,
        client_assets=intake.client_assets,
        supplies=intake.supplies,
        blocking_questions=tuple(questions),
    )
