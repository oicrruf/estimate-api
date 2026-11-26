"""Inactive Coolify deploy proposal: strict gates before a single scoped POST."""

from __future__ import annotations

import json
import os
import re
import ssl
import sys
import time
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, ProxyHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(
        self, req: Request, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> None:
        raise HTTPError(req.full_url, code, "Redirect refused", headers, fp)


def checked_origin(value: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
        or "REPLACE" in value
    ):
        raise ValueError("A literal, owner-approved HTTPS origin is required")
    return value.rstrip("/")


def configured() -> tuple[str, str, str, str]:
    if os.environ.get("GITHUB_REPOSITORY") != "oicrruf/estimate-api":
        raise ValueError("Repository gate failed")
    if os.environ.get("GITHUB_REF") != "refs/heads/develop":
        raise ValueError("Protected develop gate failed")
    if os.environ.get("COOLIFY_BRANCH_POLICY_CONFIRMED") != "YES":
        raise ValueError("Owner must configure coolify Environment branch protection first")
    admin = checked_origin(os.environ.get("COOLIFY_ORIGIN", ""))
    demo = checked_origin(os.environ.get("COOLIFY_DEMO_ORIGIN", ""))
    if urlsplit(admin).netloc == urlsplit(demo).netloc:
        raise ValueError("Demo URL must differ from the administration origin")
    uuid = os.environ.get("COOLIFY_RESOURCE_UUID", "")
    if not re.fullmatch(r"[A-Za-z0-9-]{16,64}", uuid):
        raise ValueError("One fixed approved resource UUID is required")
    token = os.environ.get("COOLIFY_TOKEN", "")
    if not token:
        raise ValueError("Environment token is missing")
    return admin, demo, uuid, token


def request_json(
    opener: Any, method: str, url: str, token: str | None, payload: dict[str, str] | None = None
) -> dict[str, Any]:
    body = json.dumps(payload, separators=(",", ":")).encode() if payload is not None else None
    headers = {"Accept": "application/json"}
    if token is not None:
        headers["Authorization"] = "Bearer " + token
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = Request(url, data=body, headers=headers, method=method)
    with opener.open(req, timeout=15) as response:
        if response.status != 200:
            raise RuntimeError(f"Unexpected HTTP status: {response.status}")
        value: Any = json.load(response)
    if not isinstance(value, dict):
        raise RuntimeError("Unexpected JSON response")
    return value


def prove_demo(opener: Any, origin: str) -> None:
    with opener.open(Request(origin + "/demo", method="GET"), timeout=15) as response:
        if response.status != 200 or b"<app-root" not in response.read():
            raise RuntimeError("Demo page proof failed")
    cases = (
        ("switch", "SW-16"),
        ("switch&poe_ports_min=12", None),
        ("camera&quantity=4", None),
        ("camera&quantity=2", "CAM-POE"),
        ("ups", None),
    )
    for query, selected in cases:
        result = request_json(opener, "GET", origin + "/v1/demo/evaluate?scenario=" + query, None)
        if result.get("selectedProductId") != selected:
            raise RuntimeError(f"Demo proof failed for {query}")
        if "storePath" in result or not all(c.get("evidencePaths") for c in result["candidates"]):
            raise RuntimeError(f"Evidence proof failed for {query}")


def main() -> int:
    try:
        admin, demo, uuid, token = configured()
        opener = build_opener(
            ProxyHandler({}), HTTPSHandler(context=ssl.create_default_context()), NoRedirect()
        )
        queued = request_json(opener, "POST", admin + "/api/v1/deploy", token, {"uuid": uuid})
        deployments = queued.get("deployments")
        if not isinstance(deployments, list) or len(deployments) != 1:
            raise RuntimeError("One deployment response was expected; inspect Coolify before retry")
        item = deployments[0]
        if item.get("resource_uuid") != uuid:
            raise RuntimeError("Unexpected resource in deployment response; inspect before retry")
        deployment_id = item.get("deployment_uuid", "")
        if not re.fullmatch(r"[A-Za-z0-9-]{8,80}", deployment_id):
            raise RuntimeError("Invalid deployment UUID; inspect before retry")
        print("Deployment queued; UUID:", deployment_id)
        for _ in range(90):
            result = request_json(
                opener, "GET", admin + "/api/v1/deployments/" + deployment_id, token
            )
            status = result.get("status")
            if status == "finished":
                prove_demo(opener, demo)
                print("Deployment finished and demo GET proof passed")
                return 0
            if status in {"failed", "cancelled", "cancelled-by-user"}:
                raise RuntimeError(f"Deployment ended with status {status}")
            time.sleep(10)
        raise RuntimeError("Deployment status timed out; inspect Coolify before retry")
    except (HTTPError, OSError, ValueError, RuntimeError, KeyError) as error:
        print(f"Coolify proposal stopped: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
