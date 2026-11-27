"""Structured, read-only intake preview backed by the AT-246 contract."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Annotated, Generic, Literal, Protocol, TypeVar

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from estimate_api.domain.scope_capture import (
    AssetAvailability,
    AssetValidation,
    Certainty,
    ClientAsset,
    Fact,
    Measurement,
    ScopeDraft,
    ScopeIntake,
    SupplyItem,
    SupplyOwner,
    build_scope_draft,
)

T = TypeVar("T")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FactPayload(StrictModel, Generic[T]):
    value: T
    certainty: Certainty
    evidence: str | None = None


class MeasurementPayload(StrictModel):
    label: str
    value: float = Field(strict=True)
    unit: str


class ClientAssetPayload(StrictModel):
    name: str
    availability: AssetAvailability
    validation: AssetValidation
    evidence: str | None = None


class SupplyItemPayload(StrictModel):
    name: str
    supplied_by: SupplyOwner
    purchase_required: bool = False


class IntakePayload(StrictModel):
    description: str = Field(min_length=1, max_length=4000)
    objective: FactPayload[str] | None = None
    location: FactPayload[str] | None = None
    environment: FactPayload[str] | None = None
    sketch: FactPayload[str] | None = None
    measurements: FactPayload[list[MeasurementPayload]] | None = None
    restrictions: FactPayload[list[str]] | None = None
    exclusions: FactPayload[list[str]] | None = None
    client_assets: list[ClientAssetPayload] = Field(default_factory=list)
    supplies: list[SupplyItemPayload] = Field(default_factory=list)
    client_assets_absence_evidence: str | None = None
    supplies_absence_evidence: str | None = None

    def to_domain(self) -> ScopeIntake:
        def text_fact(value: FactPayload[str] | None) -> Fact[str] | None:
            return None if value is None else Fact(value.value, value.certainty, value.evidence)

        def list_fact(value: FactPayload[list[str]] | None) -> Fact[tuple[str, ...]] | None:
            return (
                None if value is None else Fact(tuple(value.value), value.certainty, value.evidence)
            )

        measures = self.measurements
        return ScopeIntake(
            description=self.description,
            objective=text_fact(self.objective),
            location=text_fact(self.location),
            environment=text_fact(self.environment),
            sketch=text_fact(self.sketch),
            measurements=(
                None
                if measures is None
                else Fact(
                    tuple(
                        Measurement(item.label, item.value, item.unit) for item in measures.value
                    ),
                    measures.certainty,
                    measures.evidence,
                )
            ),
            restrictions=list_fact(self.restrictions),
            exclusions=list_fact(self.exclusions),
            client_assets=tuple(
                ClientAsset(item.name, item.availability, item.validation, item.evidence)
                for item in self.client_assets
            ),
            supplies=tuple(
                SupplyItem(item.name, item.supplied_by, item.purchase_required)
                for item in self.supplies
            ),
            client_assets_absence_evidence=self.client_assets_absence_evidence,
            supplies_absence_evidence=self.supplies_absence_evidence,
        )


class IntakePreviewRequest(StrictModel):
    operation: Literal["create_project"]
    intake: IntakePayload


class BlockingQuestionPayload(StrictModel):
    field: str
    text: str


class ScopeDraftPayload(IntakePayload):
    contract_version: str
    blocking_questions: list[BlockingQuestionPayload]


class IntakePreviewResponse(StrictModel):
    stage: Literal["scope_review_pending"] = "scope_review_pending"
    review_required: Literal[True] = True
    persisted: Literal[False] = False
    project_id: None = None
    draft: ScopeDraftPayload
    proposed_purchase_items: list[str]


class ScopePreviewService(Protocol):
    def preview(self, intake: ScopeIntake) -> ScopeDraft: ...


class LocalScopePreviewService:
    def preview(self, intake: ScopeIntake) -> ScopeDraft:
        return build_scope_draft(intake)


def get_scope_preview_service() -> ScopePreviewService:
    """Replace with AT-240 discovery after its contract is integrated."""
    return LocalScopePreviewService()


router = APIRouter(prefix="/v1/chat", tags=["chat"])


@router.post(
    "/intake-preview",
    operation_id="previewChatIntake",
    response_model=IntakePreviewResponse,
)
def preview_chat_intake(
    request: IntakePreviewRequest,
    service: Annotated[ScopePreviewService, Depends(get_scope_preview_service)],
) -> IntakePreviewResponse:
    """Return a review proposal; no confirmation or mutation path exists here."""
    try:
        draft = service.preview(request.intake.to_domain())
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return IntakePreviewResponse(
        draft=ScopeDraftPayload.model_validate_json(json.dumps(asdict(draft), allow_nan=False)),
        proposed_purchase_items=list(draft.purchase_items),
    )
