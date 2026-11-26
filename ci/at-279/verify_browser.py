"""Exercise the real Angular demo in a local headless browser via WebDriver."""

from __future__ import annotations

import json
import shutil
import socket
import subprocess
import tempfile
import time
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

ORIGIN = "http://127.0.0.1:8080"


class Driver:
    def __init__(self, port: int) -> None:
        self.base = f"http://127.0.0.1:{port}"
        self.session = ""

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        body = json.dumps(payload).encode() if payload is not None else None
        req = Request(
            self.base + path,
            data=body,
            headers={"Content-Type": "application/json"} if body is not None else {},
            method=method,
        )
        # A fresh Chrome session may take longer on a loaded hosted runner.
        timeout = 45 if path == "/session" else 15
        with urlopen(req, timeout=timeout) as response:
            answer = json.load(response)
        value: Any = answer["value"]
        if isinstance(value, dict) and value.get("error"):
            raise RuntimeError(value["error"])
        return value

    def execute(self, script: str) -> Any:
        return self.request(
            "POST", f"/session/{self.session}/execute/sync", {"script": script, "args": []}
        )

    def click_submit(self) -> None:
        element = self.request(
            "POST",
            f"/session/{self.session}/element",
            {"using": "css selector", "value": "button[type=submit]"},
        )
        element_id = element["element-6066-11e4-a52e-4f735466cecf"]
        self.request("POST", f"/session/{self.session}/element/{element_id}/click", {})

    def wait_text(self, expected: str) -> None:
        for _ in range(80):
            text = self.execute(
                "return document.querySelector('.decision-head')?.textContent?.trim()"
            )
            if text == expected:
                return
            time.sleep(0.2)
        raise AssertionError(f"Expected decision not shown: {expected}")


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def main() -> None:
    executable = shutil.which("chromedriver")
    if executable is None:
        raise RuntimeError("The standard runner must provide chromedriver")
    port = free_port()
    driver = Driver(port)
    with tempfile.TemporaryDirectory(prefix="at279-browser-") as profile:
        service = subprocess.Popen(
            [executable, f"--port={port}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            for _ in range(80):
                try:
                    if driver.request("GET", "/status")["ready"]:
                        break
                except URLError:
                    time.sleep(0.1)
            else:
                raise RuntimeError("ChromeDriver did not start")
            browser = shutil.which("google-chrome") or shutil.which("chromium")
            if browser is None:
                raise RuntimeError("The standard runner must provide Chrome or Chromium")
            options = {
                "browserName": "chrome",
                "goog:chromeOptions": {
                    "binary": browser,
                    "args": [
                        "--headless=new",
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--window-size=1280,900",
                        f"--user-data-dir={profile}",
                    ],
                },
            }
            result = driver.request("POST", "/session", {"capabilities": {"alwaysMatch": options}})
            driver.session = result["sessionId"]
            driver.request("POST", f"/session/{driver.session}/url", {"url": ORIGIN + "/demo"})
            for _ in range(80):
                if driver.execute("return !!document.querySelector('button[type=submit]')"):
                    break
                time.sleep(0.2)
            else:
                raise RuntimeError("Angular demo did not render")

            driver.click_submit()
            driver.wait_text("Elegible: SW-16")
            assert driver.execute("return !!document.querySelector('article.candidate details')")
            print("Angular switch8: SW-16 with evidence")

            driver.execute("document.querySelectorAll('input[name=poe]')[1].click()")
            driver.click_submit()
            driver.wait_text("Sin producto adquirible elegible")
            print("Angular switch12: no eligible product")

            driver.execute(
                "const s=document.querySelector('#scenario'); s.value='camera';"
                "s.dispatchEvent(new Event('change',{bubbles:true}))"
            )
            driver.click_submit()
            driver.wait_text("Inventario insuficiente")
            stock = driver.execute(
                "return document.querySelector('.stock strong')?.textContent?.trim()"
            )
            assert stock == "2"
            print("Angular camera4: shared pool 2")

            driver.execute("document.querySelectorAll('input[name=quantity]')[0].click()")
            driver.click_submit()
            driver.wait_text("Elegible: CAM-POE")
            print("Angular camera2: CAM-POE")

            driver.execute(
                "const s=document.querySelector('#scenario'); s.value='ups';"
                "s.dispatchEvent(new Event('change',{bubbles:true}))"
            )
            driver.click_submit()
            driver.wait_text("Compatible técnicamente, sin oferta")
            print("Angular UPS: technically viable without offer")

            requests = driver.execute(
                "return performance.getEntriesByType('resource')"
                ".map(entry=>entry.name).filter(name=>name.includes('/v1/demo/evaluate'))"
            )
            assert len(requests) >= 5, requests
            assert all(url.startswith(ORIGIN + "/v1/demo/evaluate?") for url in requests)
            print(f"Browser same-origin API requests: {len(requests)}")
        finally:
            if driver.session:
                try:
                    driver.request("DELETE", f"/session/{driver.session}")
                except (OSError, ValueError):
                    pass
            service.terminate()
            service.wait(timeout=10)


if __name__ == "__main__":
    main()
