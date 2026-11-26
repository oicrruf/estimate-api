"""Entrada CLI real de AT-227 con procesos separados y grafo Relate sintético."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import pytest

pytest.importorskip("google.adk")


def cli(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "demo.agent.cli", *args],
        capture_output=True,
        check=check,
        text=True,
    )


def output(*args: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(cli(*args).stdout))


def evidence_ids(candidate: dict[str, Any]) -> set[str]:
    for path in candidate["evidencePaths"]:
        assert len(path["nodes"]) == len(path["relations"]) + 1
        assert all(
            node["type"] in {"REQUIREMENT", "PRODUCT", "CAPABILITY", "EVIDENCE"}
            for node in path["nodes"]
        )
        assert all(
            "fictici" in node["source"] for node in path["nodes"] if node["type"] == "EVIDENCE"
        )
    return {
        node["id"]
        for path in candidate["evidencePaths"]
        for node in path["nodes"]
        if node["type"] == "EVIDENCE"
    }


def test_seed_and_switch_changed_requirement_reopen_from_other_process(tmp_path: Path) -> None:
    store = tmp_path / "evidence.rl"
    initial = output("seed", "--store", str(store))
    assert (initial["nodes"], initial["relationships"]) == (60, 61)
    assert store.is_file()
    assert output("seed", "--store", str(store))["nodes"] == 60

    eight = output("evaluate", "--store", str(store), "--scenario", "switch")
    assert eight["engine"] == "google-adk-custom-agent-offline"
    assert eight["tool"] == "switch_evidence"
    assert eight["selectedProductId"] == "SW-16"
    candidates = {item["productId"]: item for item in eight["candidates"]}
    assert candidates["SW-8"]["status"] == "INCOMPATIBLE"
    assert "TOTAL_PORTS_BELOW_REQUIRED" in candidates["SW-8"]["reasonCodes"]
    assert candidates["SW-8"]["fictitiousPriceUsd"] == 80
    assert candidates["SW-16"]["status"] == "COMPATIBLE"
    assert "EV-SW16" in evidence_ids(candidates["SW-16"])

    twelve = output(
        "evaluate", "--store", str(store), "--scenario", "switch", "--poe-ports-min", "12"
    )
    assert twelve["requested"]["totalPortsMin"] == 13
    assert twelve["selectedProductId"] is None
    changed = {item["productId"]: item for item in twelve["candidates"]}
    assert changed["SW-16"]["measured"]["poePorts"] == 8
    assert "POE_PORTS_BELOW_REQUIRED" in changed["SW-16"]["reasonCodes"]
    assert "EV-SW16" in evidence_ids(changed["SW-16"])


def test_pool_and_second_domain(tmp_path: Path) -> None:
    store = tmp_path / "evidence.rl"
    output("seed", "--store", str(store))
    four = output("evaluate", "--store", str(store), "--scenario", "camera")
    assert four["requestedQuantity"] == 4
    assert four["availableQuantity"] == 2
    assert four["selectedProductId"] is None
    candidate = four["candidates"][0]
    assert candidate["offerIds"] == ["OFF-CAM-A", "OFF-CAM-B"]
    assert candidate["status"] == "INSUFFICIENT_STOCK"
    assert "EV-POOL-CAM" in evidence_ids(candidate)

    two = output("evaluate", "--store", str(store), "--scenario", "camera", "--quantity", "2")
    assert two["availableQuantity"] == 2
    assert two["selectedProductId"] == "CAM-POE"
    assert two["candidates"][0]["status"] == "COMPATIBLE"

    ups = output("evaluate", "--store", str(store), "--scenario", "ups")
    assert ups["selectedProductId"] is None  # Sin oferta, sólo compatibilidad técnica.
    assert ups["candidates"][0]["status"] == "TECHNICALLY_COMPATIBLE_NO_OFFER"
    assert "EV-UPS-1500" in evidence_ids(ups["candidates"][0])


def test_demo_command_and_help(tmp_path: Path) -> None:
    store = tmp_path / "evidence.rl"
    demo = output("demo", "--store", str(store))
    assert demo["mode"] == "offline-adk"
    assert [run["scenario"] for run in demo["runs"]] == [
        "switch",
        "switch",
        "camera",
        "camera",
        "ups",
    ]
    assert demo["seed"]["nodes"] == 60
    assert "--store" in cli("evaluate", "--help").stdout


@pytest.mark.parametrize(
    "args",
    [
        ("--scenario", "switch", "--poe-ports-min", "0"),
        ("--scenario", "switch", "--poe-ports-min", "12; MATCH (n) DELETE n"),
        ("--scenario", "ups", "--poe-ports-min", "8"),
        ("--scenario", "switch", "--quantity", "4"),
    ],
)
def test_invalid_arguments_are_rejected(tmp_path: Path, args: tuple[str, ...]) -> None:
    store = tmp_path / "evidence.rl"
    output("seed", "--store", str(store))
    result = cli("evaluate", "--store", str(store), *args, check=False)
    assert result.returncode == 2
    assert not result.stdout
    assert output("seed", "--store", str(store))["nodes"] == 60


def test_missing_or_foreign_store_is_rejected(tmp_path: Path) -> None:
    store = tmp_path / "evidence.rl"
    missing = cli("evaluate", "--store", str(store), "--scenario", "ups", check=False)
    assert missing.returncode == 2
    assert not store.exists()

    import relate

    conn = relate.connect(str(store))
    conn.execute("CREATE (:OTHER {id:'external'})")
    conn.close()
    foreign = cli("seed", "--store", str(store), check=False)
    assert foreign.returncode == 2
    conn = relate.connect(str(store), read_only=True)
    assert conn.execute("MATCH (n) RETURN count(n) AS n").single()["n"] == 1
    conn.close()
