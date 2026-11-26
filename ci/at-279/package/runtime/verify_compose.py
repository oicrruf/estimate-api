"""Verificar que Compose no publica la API ni abre Nginx fuera de loopback."""

import json
import subprocess

raw = subprocess.check_output(["docker", "compose", "config", "--format", "json"], text=True)
configuration = json.loads(raw)
services = configuration["services"]
api = services["api"]
seed = services["seed"]
web = services["web"]
assert not api.get("ports") and not seed.get("ports")
assert len(web["ports"]) == 1
assert web["ports"][0]["host_ip"] == "127.0.0.1"
assert web["ports"][0]["target"] == 8080
assert configuration["networks"]["backplane"]["internal"] is True
assert set(api["networks"]) == {"backplane"}
assert set(web["networks"]) == {"backplane", "edge"}
assert api["read_only"] and seed["read_only"] and web["read_only"]
assert int(api["mem_limit"]) <= 1024**3 and int(web["mem_limit"]) <= 128 * 1024**2
assert api["pids_limit"] <= 128 and web["pids_limit"] <= 64
assert all("ALL" in service["cap_drop"] for service in (seed, api, web))
assert any(volume["target"] == "/data" and volume["read_only"] for volume in api["volumes"])
print("Compose privado: API sin puerto publicado, web sólo loopback, recursos acotados")
