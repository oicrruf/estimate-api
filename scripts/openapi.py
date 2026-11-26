"""Export or verify the canonical deterministic OpenAPI document."""

import argparse
import json
from pathlib import Path

from estimate_api.app import app

ARTIFACT = Path(__file__).resolve().parents[1] / "contracts" / "openapi.json"


def render() -> str:
    return json.dumps(app.openapi(), ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = render()
    if args.check:
        if not ARTIFACT.exists() or ARTIFACT.read_text() != expected:
            print(f"OpenAPI drift: regenerate {ARTIFACT} with python scripts/openapi.py")
            return 1
        print(f"OpenAPI matches {ARTIFACT}")
        return 0
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(expected)
    print(ARTIFACT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
