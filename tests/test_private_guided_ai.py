"""Verifica la frontera privada sin llamadas a proveedor."""

import asyncio
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("google.adk")

import demo.guided_bom.private_ai as private_module
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
        assert result["evidenceIds"] == []
        assert result["toolCalls"] == 0
        assert result["status"] == "NEEDS_INPUT"


@pytest.mark.parametrize(
    ("description", "count", "variant", "expected"),
    [
        (
            "Seis UTP de OD 0.278 in; tramos de 2 m y 1.5 m.",
            6,
            "thick",
            "GEN-EMT-1-1-4",
        ),
        (
            "Six UTP cables with outer diameter 0.224 inches; segments of 2 m and 1.5 m.",
            6,
            "slim",
            "GEN-EMT-1",
        ),
    ],
)
def test_complete_es_en_measurements_use_relate(
    description: str, count: int, variant: str, expected: str
) -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "guided.rl"
        seed(path)
        result = asyncio.run(run_private(path, description, FakeExtractor(count, variant, "known")))
        assert result["toolCalls"] == 1
        assert result["preview"]["status"]["selectedDemoEmtId"] == expected
        assert result["preview"]["bom"]
        assert "EV-ROUTE-CONFIRMED" in result["evidenceIds"]


def test_fail_closed_on_unsupported_model_claims() -> None:
    raw = {
        "cable_count": 6,
        "cable_variant": "thick",
        "route_length": "known",
        "missing": [],
    }
    with pytest.raises(ValueError, match="Cantidad UTP sin respaldo"):
        _validated_scope("Tres cámaras Wi-Fi.", raw)
    with pytest.raises(ValueError, match="OD sin respaldo"):
        _validated_scope("Seis UTP sin ficha.", raw)
    with pytest.raises(ValueError, match="Longitudes sin respaldo"):
        _validated_scope("Seis UTP de OD 0.278 in.", raw)


@pytest.mark.parametrize(
    "description",
    [
        "Seis UTP de OD 0.278 in; tramos de 12 m y 11.5 m.",
        "Seis UTP de OD 0.278 mm; tramos de 2 m y 1.5 m.",
        "Seis UTP de OD 10.278 in; tramos de 2 m y 1.5 m.",
        "Seis UTP de OD 0.2788 in; tramos de 2 m y 1.5 m.",
        "Tres UTP y seis UTP de OD 0.278 in; tramos de 2 m y 1.5 m.",
        "Seis UTP de OD 0.278 in y OD 0.224 in; tramos de 2 m y 1.5 m.",
        "Seis UTP 10GXS32; tramos de 2 m y 1.5 m.",
        "Six UTP cables with outer diameter 0.278 mm; segments of 2 m and 1.5 m.",
        "Six UTP cables with outer diameter 0.278 inches; segments of 12 m and 11.5 m.",
    ],
)
def test_mismatched_or_conflicting_measurements_fail_before_graph(
    description: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "guided.rl"
        seed(path)

        def forbidden(*args: object, **kwargs: object) -> None:
            raise AssertionError("No se debe abrir Relate")

        monkeypatch.setattr("demo.guided_bom.private_ai.graph_evidence", forbidden)
        with pytest.raises(ValueError):
            asyncio.run(run_private(path, description, FakeExtractor(6, "thick", "known")))


def test_missing_od_skips_graph(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "guided.rl"
        seed(path)

        def forbidden(*args: object, **kwargs: object) -> None:
            raise AssertionError("No se debe abrir Relate")

        monkeypatch.setattr("demo.guided_bom.private_ai.graph_evidence", forbidden)
        result = asyncio.run(
            run_private(path, "Seis UTP sin OD medido.", FakeExtractor(6, "unknown", "unknown"))
        )
        assert result["toolCalls"] == 0
        assert result["preview"] is None
        assert result["status"] == "NEEDS_INPUT"


def test_private_cli_entry_uses_fake_provider_and_real_graph(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "guided.rl"
        seed(path)
        models: list[str] = []

        def extractor(model: str) -> FakeExtractor:
            models.append(model)
            return FakeExtractor(6, "thick", "known")

        monkeypatch.setattr(private_module, "OpenAIScopeExtractor", extractor)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "private_ai",
                "--store",
                str(path),
                "--description",
                "Seis UTP de OD 0.278 in; tramos de 2 m y 1.5 m.",
            ],
        )
        assert private_module.main() == 0
        result = json.loads(capsys.readouterr().out)
        assert models == ["gpt-6-luna"]
        assert result["toolCalls"] == 1
        assert result["preview"]["status"]["selectedDemoEmtId"] == "GEN-EMT-1-1-4"


def test_rejects_long_description_before_model() -> None:
    fake = FakeExtractor(None, "unknown", "unknown")
    with pytest.raises(ValueError, match="700 caracteres"):
        asyncio.run(run_private(Path("/does/not/matter"), "x" * 701, fake))
    assert fake.calls == 0
