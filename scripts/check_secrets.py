"""Fail on findings from pinned detect-secrets scanner in tracked files."""

import json
import subprocess
import sys


def main() -> int:
    files = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"], text=True
    ).splitlines()
    files = [
        name
        for name in files
        if name != "uv.lock" and not name.startswith("ci/at-206-docs/package-lock")
    ]
    result = subprocess.run(
        ["detect-secrets", "scan", *files], capture_output=True, text=True, check=True
    )
    findings = json.loads(result.stdout)["results"]
    if findings:
        print("Potential secrets detected in: " + ", ".join(sorted(findings)), file=sys.stderr)
        return 1
    print("No potential secrets detected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
