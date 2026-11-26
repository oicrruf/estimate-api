"""Explicit private container entry point; local CLI retains its loopback bind."""

import os
from pathlib import Path

import uvicorn

from demo.preview_api import create_app

if os.environ.get("AT279_INTERNAL_CONTAINER_MODE") != "1":
    raise SystemExit("Internal container mode is required")

app = create_app(Path("/data/estimate-at278.rl"))
uvicorn.run(app, host="0.0.0.0", port=8001, proxy_headers=False, access_log=False)
