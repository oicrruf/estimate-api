"""Exercise the Git-source Coolify candidate without a host port or external service."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

RUNTIME = Path(__file__).resolve().parent
COMPOSE = "coolify-compose.yaml"
STORE = "/data/estimate-at278.rl"
PROBE = r"""
import json
from urllib.request import urlopen

base = "http://web:8080"
with urlopen(base + "/demo", timeout=10) as response:
    assert response.status == 200 and b"<app-root" in response.read()
cases = (
    ("switch", "SW-16", "COMPATIBLE"),
    ("switch&poe_ports_min=12", None, "INCOMPATIBLE"),
    ("camera&quantity=4", None, "INSUFFICIENT_STOCK"),
    ("camera&quantity=2", "CAM-POE", "COMPATIBLE"),
    ("ups", None, "TECHNICALLY_COMPATIBLE_NO_OFFER"),
)
for query, selected, status in cases:
    with urlopen(base + "/v1/demo/evaluate?scenario=" + query, timeout=15) as response:
        assert response.status == 200
        result = json.load(response)
    assert result["selectedProductId"] == selected, query
    assert any(candidate["status"] == status for candidate in result["candidates"]), query
    assert all(candidate["evidencePaths"] for candidate in result["candidates"]), query
    assert "storePath" not in result
    print(query, selected, status)
"""


def command(*args: str) -> str:
    result = subprocess.run(args, cwd=RUNTIME, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def compose(*args: str) -> str:
    return command("docker", "compose", "-f", COMPOSE, *args)


def inspect(container: str, expression: str) -> str:
    return command("docker", "inspect", "--format", expression, container)


def assert_layout() -> tuple[str, str]:
    config = json.loads(compose("config", "--format", "json"))
    services = config["services"]
    assert set(services) == {"api", "seed", "web"}
    assert all(not service.get("ports") for service in services.values())
    assert services["web"]["expose"] == ["8080"]
    assert config["networks"]["backplane"]["internal"] is True
    assert set(services["api"]["networks"]) == {"backplane"}
    assert set(services["seed"]["networks"]) == {"backplane"}
    assert set(services["web"]["networks"]) == {"backplane", "edge"}
    assert all(service["read_only"] for service in services.values())
    assert all("ALL" in service["cap_drop"] for service in services.values())
    assert all(not service.get("privileged") for service in services.values())
    assert not any(
        "/var/run/docker.sock" in str(service.get("volumes", "")) for service in services.values()
    )
    assert any(
        volume["target"] == "/data" and volume["read_only"] for volume in services["api"]["volumes"]
    )
    seed_id = compose("ps", "-aq", "seed")
    api_id = compose("ps", "-q", "api")
    web_id = compose("ps", "-q", "web")
    assert seed_id and api_id and web_id
    for container in (seed_id, api_id, web_id):
        assert inspect(container, "{{json .HostConfig.PortBindings}}") in ("null", "{}")
    networks = json.loads(inspect(api_id, "{{json .NetworkSettings.Networks}}"))
    assert len(networks) == 1
    assert (
        command("docker", "network", "inspect", "--format", "{{.Internal}}", next(iter(networks)))
        == "true"
    )
    mounts = json.loads(inspect(api_id, "{{json .Mounts}}"))
    assert any(mount["Destination"] == "/data" and not mount["RW"] for mount in mounts)
    return seed_id, api_id


def probe() -> None:
    print(compose("exec", "-T", "api", "/app/.venv/bin/python", "-c", PROBE))


def main() -> None:
    seed_id, api_id = assert_layout()
    assert '"store": "created"' in command("docker", "logs", seed_id)
    probe()
    before = compose("exec", "-T", "api", "sha256sum", STORE).split()[0]
    compose("stop", "api")
    assert '"store": "reused"' in command("docker", "start", "-a", seed_id)
    compose("start", "api")
    for _ in range(30):
        if inspect(api_id, "{{.State.Health.Status}}") == "healthy":
            break
        time.sleep(2)
    else:
        raise RuntimeError("API did not recover")
    probe()
    assert compose("exec", "-T", "api", "sha256sum", STORE).split()[0] == before
    compose("down")  # Keep the named volume, as a normal Compose replacement does.
    compose("up", "--no-build", "-d")
    redeploy_seed_id, _ = assert_layout()
    assert '"store": "reused"' in command("docker", "logs", redeploy_seed_id)
    probe()
    assert compose("exec", "-T", "api", "sha256sum", STORE).split()[0] == before
    print("Git Compose: host ports 0; private API; seed reused; store stable after redeploy")


if __name__ == "__main__":
    main()
