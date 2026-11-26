"""Crear la fixture sólo una vez; verificar sin escribir en arranques posteriores."""

import json
from pathlib import Path

from demo.agent.graph import seed_store
from demo.preview_api import _validate_store

store = Path("/data/estimate-at278.rl")
if store.exists():
    _validate_store(store)
    print(json.dumps({"store": "reused", "dataset": "estimate-hackathon-v1"}))
else:
    print(json.dumps({"store": "created", **seed_store(store)}))
