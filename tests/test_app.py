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
    assert set(schema["paths"]) == {"/health"}
    operation = schema["paths"]["/health"]["get"]
    assert operation["operationId"] == "health"
    assert "200" in operation["responses"]
