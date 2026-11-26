"""Synthetic AT-246 acceptance examples and adapter boundary checks."""

import json
from pathlib import Path

import pytest

from estimate_api.contracts.universal_v1 import validate_project_document
from estimate_api.domain.scope_capture import (
    AssetAvailability,
    AssetValidation,
    Certainty,
    ClientAsset,
    Fact,
    Measurement,
    ScopeAdapterError,
    ScopeIntake,
    SupplyItem,
    SupplyOwner,
    attach_scope_draft,
    build_scope_draft,
)


@pytest.fixture
def unconfirmed_cabinet() -> ScopeIntake:
    return ScopeIntake(
        description="Fit a client-supplied cabinet at a fictional workshop.",
        location=Fact("north wall", Certainty.INFERRED),
        client_assets=(
            ClientAsset("cabinet", AssetAvailability.AVAILABLE, AssetValidation.UNVALIDATED),
        ),
        supplies=(SupplyItem("fasteners", SupplyOwner.CONTRACTOR, purchase_required=True),),
    )


@pytest.fixture
def source_document() -> object:
    path = Path(__file__).resolve().parents[2] / "fixtures/valid/cameras.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_incomplete_description_produces_specific_questions_without_facts() -> None:
    intake = ScopeIntake(description="Install equipment at a fictional workshop.")
    draft = build_scope_draft(intake)
    assert {question.field for question in draft.blocking_questions} == {
        "objective",
        "location",
        "environment",
        "sketch",
        "measurements",
        "restrictions",
        "exclusions",
        "client_assets",
        "supplies",
    }
    assert draft.objective is None
    assert draft.location is None
    assert draft.purchase_items == ()
    assert draft == build_scope_draft(intake)


def test_inferred_fact_and_unconfirmed_cabinet(unconfirmed_cabinet: ScopeIntake) -> None:
    draft = build_scope_draft(unconfirmed_cabinet)
    assert draft.location is not None
    assert draft.location.certainty == Certainty.INFERRED
    questions = {question.field: question.text for question in draft.blocking_questions}
    assert "confirm" in questions["location"]
    assert "compatibility" in questions["client_assets.cabinet.validation"]
    assert draft.client_assets[0].supplied_by == SupplyOwner.CLIENT
    assert not draft.client_assets[0].purchase_required
    assert draft.purchase_items == ("fasteners",)


def test_complete_explicit_intake_has_no_blocking_questions() -> None:
    evidence = "fictional client intake form"
    intake = ScopeIntake(
        description="Install a display at a fictional workshop.",
        objective=Fact("Install display", Certainty.CONFIRMED, evidence),
        location=Fact("Workshop A, north wall", Certainty.CONFIRMED, evidence),
        environment=Fact("Indoor, dry", Certainty.CONFIRMED, evidence),
        sketch=Fact("Sketch SK-1", Certainty.CONFIRMED, evidence),
        measurements=Fact((Measurement("wall width", 3.0, "m"),), Certainty.CONFIRMED, evidence),
        restrictions=Fact(("Access after 9:00",), Certainty.CONFIRMED, evidence),
        exclusions=Fact((), Certainty.CONFIRMED, evidence),
        client_assets=(
            ClientAsset(
                "cabinet", AssetAvailability.AVAILABLE, AssetValidation.VALIDATED, evidence
            ),
        ),
        supplies=(SupplyItem("fasteners", SupplyOwner.CONTRACTOR, True),),
    )
    assert build_scope_draft(intake).blocking_questions == ()


def test_confirmed_empty_assets_and_supplies_clear_questions() -> None:
    draft = build_scope_draft(
        ScopeIntake(
            description="Inspect a fictional empty room.",
            client_assets_absence_evidence="client confirmed no existing assets",
            supplies_absence_evidence="client confirmed no supplied items",
        )
    )
    fields = {question.field for question in draft.blocking_questions}
    assert "client_assets" not in fields
    assert "supplies" not in fields
    assert draft.client_assets_absence_evidence is not None
    assert draft.supplies_absence_evidence is not None


def test_adapter_validates_and_preserves_source(
    unconfirmed_cabinet: ScopeIntake, source_document: object
) -> None:
    before = json.dumps(source_document, sort_keys=True)
    document = attach_scope_draft(
        source_document, build_scope_draft(unconfirmed_cabinet), "scope:draft"
    )
    assert validate_project_document(document).valid
    assert json.dumps(source_document, sort_keys=True) == before
    package = document["packages"][-1]
    assert package["namespace"] == "estimate.scope-capture"
    assert package["subjectId"] == document["projectId"]
    facts = package["facts"]
    assert facts["purchaseItems"] == ["fasteners"]
    location = facts["location"]
    assert isinstance(location, dict)
    assert location["certainty"] == "inferred"
    client_assets = facts["client_assets"]
    assert isinstance(client_assets, list)
    cabinet = client_assets[0]
    assert isinstance(cabinet, dict)
    assert cabinet["validation"] == "unvalidated"


def test_adapter_rejects_invalid_source_and_duplicate_package(
    unconfirmed_cabinet: ScopeIntake, source_document: object
) -> None:
    draft = build_scope_draft(unconfirmed_cabinet)
    with pytest.raises(ScopeAdapterError, match="invalid source document"):
        attach_scope_draft({"schemaVersion": "unsupported"}, draft, "scope:draft")
    validated = attach_scope_draft(source_document, draft, "scope:draft")
    with pytest.raises(ScopeAdapterError, match="duplicate id"):
        attach_scope_draft(validated, draft, "scope:draft")
    with pytest.raises(ScopeAdapterError, match="invalid mapped document"):
        attach_scope_draft(source_document, draft, "bad id")


def test_invalid_confirmation_and_purchase_claims_are_rejected() -> None:
    with pytest.raises(ValueError, match="explicit evidence"):
        Fact("north wall", Certainty.CONFIRMED)
    with pytest.raises(ValueError, match="cannot be marked for purchase"):
        SupplyItem("cabinet", SupplyOwner.CLIENT, True)
    with pytest.raises(ValueError, match="only available"):
        ClientAsset(
            "cabinet", AssetAvailability.UNAVAILABLE, AssetValidation.VALIDATED, "inspection"
        )
    with pytest.raises(ValueError, match="SupplyOwner"):
        SupplyItem("cabinet", "vendor")  # type: ignore[arg-type]
    for invalid in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError, match="finite positive"):
            Measurement("width", invalid, "m")
    with pytest.raises(ValueError, match="absence evidence"):
        ScopeIntake("fictional request", client_assets_absence_evidence=" ")
    with pytest.raises(ValueError, match="absence evidence"):
        ScopeIntake(
            "fictional request",
            client_assets=(
                ClientAsset("cabinet", AssetAvailability.AVAILABLE, AssetValidation.UNKNOWN),
            ),
            client_assets_absence_evidence="client confirmed none",
        )
    with pytest.raises(ValueError, match="unique"):
        ScopeIntake(
            "fictional request",
            client_assets=(
                ClientAsset(" Cabinet ", AssetAvailability.UNKNOWN, AssetValidation.UNKNOWN),
            ),
            supplies=(SupplyItem("cabinet", SupplyOwner.CONTRACTOR),),
        )
