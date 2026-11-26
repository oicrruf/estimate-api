"""Verifica la frontera privada sin llamadas a proveedor."""

import asyncio
import tempfile
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("google.adk")

from demo.guided_bom.cli import seed
from demo.guided_bom.private_ai import _validated_scope, run_private


class FakeExtractor:
    def __init__(self, count: int | None, variant: str, length: str) -> None:
        self.calls = 0
        self.raw: dict[str, Any] = {
            "cable_count": count,
            "cable_variant": variant,
            "route_length": length,
            "missing": [],
        }

    async def extract(self, description: str) -> tuple[dict[str, Any], dict[str, int]]:
        self.calls += 1
        return self.raw, {"inputTokens": 20, "outputTokens": 15}


def test_one_fake_model_call_then_real_relate() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "guided.rl"
        seed(path)
        extractor = FakeExtractor(6, "thick", "unknown")
        result = asyncio.run(
            run_private(path, "Seis UTP de OD 0.278 in; tres cámaras Wi-Fi.", extractor)
        )
        assert extractor.calls == 1
        assert result["scope"]["questions"] == ["¿Cuáles son las longitudes medidas de los tramos?"]
        assert result["scope"]["states"]["routeLength"] == "unknown"
        assert result["preview"]["status"]["selectedDemoEmtId"] == "GEN-EMT-1-1-4"
        assert result["preview"]["bom"] == []
        assert "EV-ROUTE-CONFIRMED" in result["evidenceIds"]
        assert result["usage"] == {"inputTokens": 20, "outputTokens": 15}


def test_missing_inputs_do_not_create_quantities() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "guided.rl"
        seed(path)
        result = asyncio.run(
            run_private(
                path, "Tres cámaras Wi-Fi sin internet.", FakeExtractor(None, "unknown", "unknown")
            )
        )
        assert result["preview"] is None
        assert len(result["scope"]["questions"]) == 3
        assert result["evidenceIds"]


def test_fail_closed_on_unsupported_model_claims() -> None:
    raw = {
        "cable_count": 6,
        "cable_variant": "thick",
        "route_length": "known",
        "missing": [],
    }
    with pytest.raises(ValueError, match="Cantidad UTP sin respaldo"):
        _validated_scope("Tres cámaras Wi-Fi.", raw)
    with pytest.raises(ValueError, match="OD grueso sin respaldo"):
        _validated_scope("Seis UTP sin ficha.", raw)
    with pytest.raises(ValueError, match="Longitud sin respaldo"):
        _validated_scope("Seis UTP de OD 0.278 in.", raw)


def test_rejects_long_description_before_model() -> None:
    fake = FakeExtractor(None, "unknown", "unknown")
    with pytest.raises(ValueError, match="700 caracteres"):
        asyncio.run(run_private(Path("/does/not/matter"), "x" * 701, fake))
    assert fake.calls == 0
