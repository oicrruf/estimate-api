"""Corte real ADK + Relate con datos artificiales y decisiones cerradas."""

import asyncio
import json
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import pytest
import relate

pytest.importorskip("google.adk")

from demo.guided_bom.cli import FIXTURE, ROOT, graph_evidence, run, seed


def _eligible(result: dict[str, Any], family: str) -> set[str]:
    return {
        item["itemId"]
        for item in result["candidates"][family]
        if item["status"] == "ELIGIBLE_FOR_DEMO"
    }


def test_three_real_iterations_change_emt_and_accessories() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "guided.rl"
        seed(path)
        rows = graph_evidence(str(path))
        assert len(rows["route"]) == 3
        assert len(rows["materials"]) == 3
        assert len(rows["accessories"]) >= 9
        seed(path)
        results = {
            (item["cableCount"], item["cableVariant"]): asyncio.run(
                run(path, item["cableCount"], item["cableVariant"])
            )
            for item in FIXTURE["iterations"]
        }
        for item in FIXTURE["iterations"]:
            result = results[(item["cableCount"], item["cableVariant"])]
            assert result["wireVersion"] == "guided-bom.v1"
            assert result["scenarioId"] == FIXTURE["scenarioId"]
            assert result["status"]["selectedDemoEmtId"] == item["expectedEmtId"]
            assert result["status"]["code"] == "PENDING_REVIEW"
            assert len(result["evidence"]["graphPaths"]) == 3
            assert all(
                path["relations"] == ["REQUIRES", "SUPPORTED_BY"]
                for path in result["evidence"]["graphPaths"]
            )
            assert result["candidates"]["switch"] == []
            assert result["candidates"]["enclosure"] == []
            assert result["evidence"]["at239DirectCameraLinks"] == 0
            assert all(line["state"] == "draft" and line["evidenceIds"] for line in result["bom"])
            assert all(candidate["evidencePaths"] for candidate in result["candidates"]["emt"])
        small = results[(6, "slim")]
        large = results[(6, "thick")]
        fewer = results[(3, "thick")]
        assert _eligible(small, "accessories") == {
            "GEN-CONNECTOR-1",
            "GEN-COUPLING-1",
            "GEN-SUPPORT-1",
        }
        assert _eligible(large, "accessories") == {
            "GEN-CONNECTOR-1-1-4",
            "GEN-COUPLING-1-1-4",
            "GEN-SUPPORT-1-1-4",
        }
        assert fewer["status"]["selectedDemoEmtId"] == "GEN-EMT-3-4"
        assert [c["fill"]["fillPercent"] for c in large["candidates"]["emt"]] == [
            "68.3",
            "42.1",
            "24.3",
        ]
        assert [c["fill"]["fillPercent"] for c in small["candidates"]["emt"]][:2] == [
            "44.3",
            "27.4",
        ]
        assert fewer["candidates"]["emt"][0]["fill"]["fillPercent"] == "34.1"
        assert "internet_service" in large["status"]["unknown"]
        assert large["candidates"]["connectivity"][0]["price"] is None
        example = json.loads(
            (ROOT / "demo/guided_bom/guided-bom.v1.example.json").read_text(encoding="utf-8")
        )
        assert example == large


def test_rejects_unlisted_input_and_foreign_store() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "guided.rl"
        seed(path)
        with pytest.raises(ValueError, match="conjunto cerrado"):
            asyncio.run(run(path, 7, "thick"))
        with pytest.raises(ValueError, match="conjunto cerrado"):
            asyncio.run(run(path, 6, "7"))
        unknown = asyncio.run(run(path, 6, "unknown"))
        assert unknown["status"]["selectedDemoEmtId"] is None
        assert unknown["status"]["compatibility"] == "PENDING_OD"
        assert unknown["bom"] == []
        no_length = asyncio.run(run(path, 6, "thick", "unknown"))
        assert no_length["status"]["selectedDemoEmtId"] == "GEN-EMT-1-1-4"
        assert no_length["bom"] == []
        assert "bom_quantities" in no_length["status"]["unknown"]
        foreign = Path(directory) / "foreign.rl"
        conn = relate.connect(str(foreign))
        try:
            conn.execute("CREATE (:FOREIGN {id:'other'})")
        finally:
            conn.close()
        with pytest.raises(ValueError, match="Store ajeno"):
            seed(foreign)


def test_real_http_matches_cli_and_rejects_unlisted_query() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "guided.rl"
        subprocess.run(
            [sys.executable, "-m", "demo.guided_bom.cli", "seed", "--store", str(path)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        store_before_get = path.read_bytes()
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        server = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "demo.guided_bom.http",
                "--store",
                str(path),
                "--port",
                str(port),
            ],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            base = f"http://127.0.0.1:{port}/v1/demo/guided-bom"
            for _ in range(70):
                try:
                    with urlopen(f"{base}?cable_count=3&cable_variant=thick", timeout=1):
                        break
                except URLError as error:
                    if server.poll() is not None:
                        raise AssertionError("Servidor HTTP local terminó antes del GET") from error
                    time.sleep(0.1)
            else:
                raise AssertionError("Servidor HTTP local no respondió")
            for variant in ("thick", "slim"):
                cli = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "demo.guided_bom.cli",
                        "evaluate",
                        "--store",
                        str(path),
                        "--cable-count",
                        "6",
                        "--cable-variant",
                        variant,
                    ],
                    cwd=ROOT,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                with urlopen(f"{base}?cable_count=6&cable_variant={variant}") as response:
                    assert response.status == 200
                    assert json.load(response) == json.loads(cli.stdout)
            with urlopen(f"{base}?cable_count=6&cable_variant=unknown") as response:
                unknown = json.load(response)
                assert unknown["status"]["selectedDemoEmtId"] is None
                assert unknown["bom"] == []
            with urlopen(
                f"{base}?cable_count=6&cable_variant=thick&route_length=unknown"
            ) as response:
                no_length = json.load(response)
                assert no_length["status"]["selectedDemoEmtId"] == "GEN-EMT-1-1-4"
                assert no_length["bom"] == []
            for bad in (
                "cable_count=7&cable_variant=thick",
                "cable_count=6&cable_variant=thick&store=/tmp/other.rl",
                "cable_count=6&cable_variant=thick&cable_variant=slim",
            ):
                with pytest.raises(HTTPError) as http_error:
                    urlopen(f"{base}?{bad}")
                assert http_error.value.code == 422
            assert path.read_bytes() == store_before_get
        finally:
            server.terminate()
            server.wait(timeout=5)
