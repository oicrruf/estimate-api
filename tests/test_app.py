from fastapi.testclient import TestClient

from estimate_api.app import app

client = TestClient(app)


def test_health_contract() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"status": "ok"}


def test_unknown_route() -> None:
    assert client.get("/unknown").status_code == 404


def test_openapi_boundary() -> None:
    schema = client.get("/openapi.json").json()
    assert schema["openapi"].startswith("3.1.")
    assert schema["info"]["version"] == "0.1.0"
    assert set(schema["paths"]) == {
        "/health",
        "/projects",
        "/projects/{project_id}",
        "/v1/projects/{projectId}/scope-review-preview",
    }
    operation = schema["paths"]["/health"]["get"]
    assert operation["operationId"] == "health"
    assert "200" in operation["responses"]
    for path, operation_id in (
        ("/projects", "listProjects"),
        ("/projects/{project_id}", "getProject"),
    ):
        project_read = schema["paths"][path]["get"]
        assert project_read["operationId"] == operation_id
        assert project_read["security"] == [{"HTTPBearer": []}]
        assert "401" in project_read["responses"]
    preview = schema["paths"]["/v1/projects/{projectId}/scope-review-preview"]["post"]
    assert preview["security"] == [{"HTTPBearer": []}]
    assert "200" in preview["responses"]
    assert "401" in preview["responses"]
