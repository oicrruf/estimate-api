"""Tests use the HTTP entry point and fictional data only."""

from fastapi.testclient import TestClient

from estimate_api.app import app
from estimate_api.chat.preview import get_scope_preview_service
from estimate_api.domain.scope_capture import ScopeDraft, ScopeIntake, build_scope_draft

client = TestClient(app)
URL = "/v1/chat/intake-preview"


def test_incomplete_intake_is_only_a_review_proposal() -> None:
    response = client.post(
        URL,
        json={
            "operation": "create_project",
            "intake": {"description": "Instalar cámaras en una oficina ficticia."},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["stage"] == "scope_review_pending"
    assert body["review_required"] is True
    assert body["persisted"] is False
    assert body["project_id"] is None
    assert body["draft"]["contract_version"] == "at246.scope-draft.v1"
    assert body["draft"]["location"] is None
    assert body["proposed_purchase_items"] == []
    assert "measurements" in {q["field"] for q in body["draft"]["blocking_questions"]}
    assert (
        response.json()
        == client.post(
            URL,
            json={
                "operation": "create_project",
                "intake": {"description": "Instalar cámaras en una oficina ficticia."},
            },
        ).json()
    )


def test_inference_and_client_cabinet_need_review() -> None:
    response = client.post(
        URL,
        json={
            "operation": "create_project",
            "intake": {
                "description": "Montar equipos en un taller ficticio.",
                "location": {"value": "pared norte", "certainty": "inferred"},
                "client_assets": [
                    {"name": "gabinete", "availability": "available", "validation": "unvalidated"}
                ],
                "supplies": [
                    {"name": "fijaciones", "supplied_by": "contractor", "purchase_required": True}
                ],
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["draft"]["location"]["certainty"] == "inferred"
    questions = {q["field"] for q in body["draft"]["blocking_questions"]}
    assert "location" in questions
    assert "client_assets.gabinete.validation" in questions
    assert body["proposed_purchase_items"] == ["fijaciones"]


def test_invalid_confirmation_or_mutation_input_fails_closed() -> None:
    base: dict[str, object] = {
        "operation": "create_project",
        "intake": {"description": "Sitio ficticio"},
    }
    assert client.post(URL, json={**base, "project_id": "existing"}).status_code == 422
    assert client.post(URL, json={**base, "operation": "update_project"}).status_code == 422
    assert client.post(URL, json={**base, "confirm": True}).status_code == 422
    assert (
        client.post(
            URL,
            json={
                **base,
                "intake": {
                    "description": "Sitio ficticio",
                    "location": {"value": "norte", "certainty": "confirmed"},
                },
            },
        ).status_code
        == 422
    )


def test_service_port_can_be_replaced_without_changing_http_contract() -> None:
    class RecordingService:
        seen: ScopeIntake | None = None

        def preview(self, intake: ScopeIntake) -> ScopeDraft:
            self.seen = intake
            return build_scope_draft(intake)

    service = RecordingService()
    app.dependency_overrides[get_scope_preview_service] = lambda: service
    try:
        response = client.post(
            URL,
            json={"operation": "create_project", "intake": {"description": "Caso ficticio"}},
        )
        assert response.status_code == 200
        assert service.seen is not None
        assert service.seen.description == "Caso ficticio"
    finally:
        app.dependency_overrides.clear()
