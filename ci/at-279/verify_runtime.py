"""Check the exact synthetic Compose stack through its public loopback entry point."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

PACKAGE = Path(__file__).resolve().parent / "package"
STORE = "/data/estimate-at278.rl"


def command(*args: str) -> str:
    result = subprocess.run(args, cwd=PACKAGE, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def compose(*args: str) -> str:
    return command("docker", "compose", *args)


def store_hash() -> str:
    return compose("exec", "-T", "api", "sha256sum", STORE).split()[0]


def smoke() -> None:
    subprocess.run(["python3", "runtime/smoke.py"], cwd=PACKAGE, check=True)


def wait_for_web() -> None:
    for _ in range(30):
        try:
            with urlopen("http://127.0.0.1:8080/demo", timeout=3) as response:
                if response.status == 200:
                    return
        except URLError:
            time.sleep(2)
    raise RuntimeError("Web did not recover after API restart")


def main() -> None:
    config = json.loads(compose("config", "--format", "json"))
    services = config["services"]
    assert not services["api"].get("ports") and not services["seed"].get("ports")
    assert len(services["web"]["ports"]) == 1
    assert services["web"]["ports"][0]["host_ip"] == "127.0.0.1"
    assert services["web"]["ports"][0]["target"] == 8080
    assert config["networks"]["backplane"]["internal"] is True
    assert set(services["api"]["networks"]) == {"backplane"}
    assert set(services["web"]["networks"]) == {"backplane", "edge"}

    seed_id = compose("ps", "-aq", "seed")
    api_id = compose("ps", "-q", "api")
    assert seed_id and api_id
    network_internal = command(
        "docker", "network", "inspect", "--format", "{{.Internal}}", "at279-final-preview_backplane"
    )
    assert network_internal == "true"
    assert '"store": "created"' in command("docker", "logs", seed_id)
    mounts = json.loads(command("docker", "inspect", "--format", "{{json .Mounts}}", api_id))
    assert any(m["Destination"] == "/data" and not m["RW"] for m in mounts)
    bindings = command("docker", "inspect", "--format", "{{json .HostConfig.PortBindings}}", api_id)
    assert bindings in ("null", "{}")
    network_json = command(
        "docker", "inspect", "--format", "{{json .NetworkSettings.Networks}}", api_id
    )
    api_networks = json.loads(network_json)
    assert set(api_networks) == {"at279-final-preview_backplane"}
    smoke()
    before = store_hash()

    compose("stop", "api")
    rerun = command("docker", "start", "-a", seed_id)
    assert '"store": "reused"' in rerun, rerun
    compose("start", "api")
    for _ in range(30):
        health = command("docker", "inspect", "--format", "{{.State.Health.Status}}", api_id)
        if health == "healthy":
            break
        time.sleep(2)
    else:
        raise RuntimeError("API did not recover after restart")
    wait_for_web()
    smoke()
    assert store_hash() == before
    print("Seed reutilizado; store sin cambios; API reabierta; HTTP de mismo origen correcto")


if __name__ == "__main__":
    main()
