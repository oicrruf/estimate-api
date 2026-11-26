"""HTTP real con procesos separados y la fixture pública AT-229."""

import json
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any, cast
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import pytest

pytest.importorskip("google.adk")


def _port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture
def server(tmp_path: Path) -> Iterator[tuple[str, Path]]:
    store = tmp_path / "synthetic.rl"
    subprocess.run(
        [sys.executable, "-m", "demo.agent.cli", "seed", "--store", str(store)],
        check=True,
        capture_output=True,
        text=True,
    )
    port = _port()
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "demo.preview_api",
            "--store",
            str(store),
            "--port",
            str(port),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(100):
            if process.poll() is not None:
                raise AssertionError("El servidor local terminó antes de escuchar")
            try:
                with urlopen(f"{url}/openapi.json", timeout=1):
                    break
            except (URLError, TimeoutError):
                time.sleep(0.1)
        else:
            raise AssertionError("El servidor local no inició")
        yield url, store
    finally:
        process.terminate()
        try:
            process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate(timeout=5)


def _get(base: str, query: str) -> dict[str, Any]:
    with urlopen(f"{base}/v1/demo/evaluate?{query}", timeout=15) as response:
        assert response.status == 200
        assert "access-control-allow-origin" not in response.headers
        return cast(dict[str, Any], json.load(response))


def test_real_http_changes_eligibility_and_preserves_evidence(
    server: tuple[str, Path],
) -> None:
    url, store = server
    eight = _get(url, "scenario=switch")
    cli = subprocess.run(
        [
            sys.executable,
            "-m",
            "demo.agent.cli",
            "evaluate",
            "--store",
            str(store),
            "--scenario",
            "switch",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    expected = json.loads(cli.stdout)
    expected.pop("storePath")
    assert eight == expected
    assert eight["selectedProductId"] == "SW-16"
    assert eight["requested"]["totalPortsMin"] == 9
    candidates = {item["productId"]: item for item in eight["candidates"]}
    assert "TOTAL_PORTS_BELOW_REQUIRED" in candidates["SW-8"]["reasonCodes"]
    assert candidates["SW-16"]["status"] == "COMPATIBLE"

    twelve = _get(url, "scenario=switch&poe_ports_min=12")
    assert twelve["selectedProductId"] is None
    assert twelve["requested"]["totalPortsMin"] == 13
    changed = {item["productId"]: item for item in twelve["candidates"]}
    assert "POE_PORTS_BELOW_REQUIRED" in changed["SW-16"]["reasonCodes"]
    assert "storePath" not in twelve
    for candidate in changed.values():
        for path in candidate["evidencePaths"]:
            assert len(path["nodes"]) == len(path["relations"]) + 1
            for node in path["nodes"]:
                if node["type"] == "EVIDENCE":
                    assert "fictici" in node["source"]


def test_shared_stock_and_ups_smoke(server: tuple[str, Path]) -> None:
    url, _ = server
    four = _get(url, "scenario=camera")
    assert four["requestedQuantity"] == 4
    assert four["availableQuantity"] == 2
    assert four["selectedProductId"] is None
    assert four["candidates"][0]["reasonCodes"] == ["SHARED_POOL_CAPACITY"]
    two = _get(url, "scenario=camera&quantity=2")
    assert two["selectedProductId"] == "CAM-POE"
    ups = _get(url, "scenario=ups")
    assert ups["selectedProductId"] is None
    assert ups["candidates"][0]["status"] == "TECHNICALLY_COMPATIBLE_NO_OFFER"


@pytest.mark.parametrize(
    "query",
    [
        "scenario=ups&quantity=4",
        "scenario=camera&poe_ports_min=8",
        "scenario=switch&quantity=2",
        "scenario=switch&poe_ports_min=0",
        "scenario=switch&poe_ports_min=17",
        "scenario=switch&poe_ports_min=8&poe_ports_min=12",
        "scenario=switch&store=/tmp/foreign.rl",
        "scenario=unknown",
        "scenario=switch&poe_ports_min=1%3BDELETE",
    ],
)
def test_invalid_queries_fail_closed(server: tuple[str, Path], query: str) -> None:
    with pytest.raises(HTTPError) as error:
        _get(server[0], query)
    assert error.value.code == 422


def test_missing_store_does_not_bootstrap(tmp_path: Path) -> None:
    store = tmp_path / "missing.rl"
    result = subprocess.run(
        [sys.executable, "-m", "demo.preview_api", "--store", str(store)],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert result.returncode == 2
    assert not store.exists()


def test_foreign_store_is_rejected(tmp_path: Path) -> None:
    import relate

    store = tmp_path / "foreign.rl"
    connection = relate.connect(str(store))
    connection.execute("CREATE (:OTHER {id:'foreign'})")
    connection.close()
    result = subprocess.run(
        [sys.executable, "-m", "demo.preview_api", "--store", str(store)],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert result.returncode == 2
    assert "fixture AT-229" in result.stderr
