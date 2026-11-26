"""Corte privado con extractor simulado y Relate verdadero; cero peticiones OpenAI."""

import asyncio
import tempfile
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("google.adk")

from demo.agent.graph import seed_store
from demo.agent.private_camera import _validated_quantity, run_camera


class FakeCameraExtractor:
    model = "gpt-6-luna"

    def __init__(self, quantity: int | None) -> None:
        self.quantity = quantity
        self.calls = 0

    async def extract(self, description: str) -> tuple[dict[str, Any], dict[str, int]]:
        self.calls += 1
        return {"requested_quantity": self.quantity}, {"httpStatus": 200, "inputTokens": 25}


@pytest.mark.parametrize(
    ("description", "quantity", "status", "selected"),
    [
        ("Solicito cuatro cámaras PoE ficticias.", 4, "INSUFFICIENT_STOCK", None),
        ("Solicito dos cámaras PoE ficticias.", 2, "COMPATIBLE", "CAM-POE"),
    ],
)
def test_camera_quantity_uses_real_relate(
    description: str, quantity: int, status: str, selected: str | None
) -> None:
    with tempfile.TemporaryDirectory() as directory:
        store = Path(directory) / "camera.rl"
        seed_store(store)
        extractor = FakeCameraExtractor(quantity)
        result = asyncio.run(run_camera(store, description, extractor))
        assert extractor.calls == 1
        assert result["model"] == "gpt-6-luna"
        assert result["toolCalls"] == 1
        assert result["requestedQuantity"] == quantity
        assert result["evaluation"]["availableQuantity"] == 2
        assert result["evaluation"]["selectedProductId"] == selected
        assert result["evaluation"]["candidates"][0]["status"] == status
        assert {"EV-CAM-POE", "EV-POOL-CAM"}.issubset(result["evidenceIds"])


def test_ambiguous_quantity_skips_relate_and_stock(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("No se debe llamar a Relate")

    monkeypatch.setattr("demo.agent.private_camera.camera_stock_evidence", forbidden)
    extractor = FakeCameraExtractor(None)
    result = asyncio.run(
        run_camera(Path("/store/not/needed"), "Quizás dos o cuatro cámaras.", extractor)
    )
    assert extractor.calls == 1
    assert result["status"] == "NEEDS_QUANTITY"
    assert result["question"]
    assert result["toolCalls"] == 0
    assert result["evaluation"] is None
    assert result["evidenceIds"] == []


def test_camera_model_claims_fail_closed() -> None:
    with pytest.raises(ValueError, match="Cantidad sin respaldo inequívoco"):
        _validated_quantity("Solicito cuatro cámaras.", {"requested_quantity": 2})
    with pytest.raises(ValueError, match="Cantidad sin respaldo inequívoco"):
        _validated_quantity("Entre dos o cuatro cámaras.", {"requested_quantity": 4})
    with pytest.raises(ValueError, match="Cantidad no permitida"):
        _validated_quantity("Solicito tres cámaras.", {"requested_quantity": 3})
    with pytest.raises(ValueError, match="fuera de esquema"):
        _validated_quantity("Solicito dos cámaras.", {"requested_quantity": 2, "price": 42})


def test_length_bound_blocks_model() -> None:
    extractor = FakeCameraExtractor(None)
    with pytest.raises(ValueError, match="700 caracteres"):
        asyncio.run(run_camera(Path("/unused"), "x" * 701, extractor))
    assert extractor.calls == 0
