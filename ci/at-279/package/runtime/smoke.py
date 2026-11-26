"""Pruebas de la entrada HTTP real del Compose local AT-279."""

import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE = "http://127.0.0.1:8080"


def read(path: str) -> dict[str, object]:
    with urlopen(BASE + path, timeout=25) as response:
        assert response.status == 200
        assert "access-control-allow-origin" not in response.headers
        value = json.load(response)
        assert isinstance(value, dict)
        assert "storePath" not in value
        return value


with urlopen(BASE + "/demo", timeout=10) as response:
    assert response.status == 200 and b"<app-root" in response.read()
print("Angular /demo: 200")

for name, query, selection, status in (
    ("switch8", "scenario=switch", "SW-16", "COMPATIBLE"),
    ("switch12", "scenario=switch&poe_ports_min=12", None, "INCOMPATIBLE"),
    ("camera4", "scenario=camera&quantity=4", None, "INSUFFICIENT_STOCK"),
    ("camera2", "scenario=camera&quantity=2", "CAM-POE", "COMPATIBLE"),
    ("ups", "scenario=ups", None, "TECHNICALLY_COMPATIBLE_NO_OFFER"),
):
    result = read("/v1/demo/evaluate?" + query)
    assert result["selectedProductId"] == selection
    candidates = result["candidates"]
    assert isinstance(candidates, list) and candidates
    assert any(candidate["status"] == status for candidate in candidates)
    assert all(candidate["evidencePaths"] for candidate in candidates)
    print(name, result["selectedProductId"], status)

for path, expected_status in (
    ("/v1/demo/evaluate?scenario=ups&quantity=2", 422),
    ("/v1/demo/evaluate?scenario=switch&store=/etc/passwd", 422),
    ("/v1/demo/openapi.json", 404),
    ("/v1/demo/seed", 404),
):
    try:
        urlopen(BASE + path, timeout=10)
    except HTTPError as error:
        assert error.code == expected_status, (path, error.code)
    else:
        raise AssertionError(path)
    print(path, expected_status)

try:
    urlopen(Request(BASE + "/v1/demo/evaluate?scenario=switch", method="POST"), timeout=10)
except HTTPError as error:
    assert error.code == 403
else:
    raise AssertionError("POST aceptado")
print("POST bloqueado: 403")
