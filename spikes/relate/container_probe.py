"""Run one synthetic step per fresh container against isolated named volumes."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import relate
from spike import ROOT, build_graph, snapshot

DATA = Path("/data/catalog.rl")
BACKUP = Path("/backup/catalog.rl")
RESTORED = Path("/restored/catalog.rl")
EXPECTED = Path("/backup/expected.json")


def check_writer_lock(path):
    owner = relate.connect(str(path))
    try:
        contender = subprocess.run(
            [
                sys.executable,
                "-c",
                "import relate,sys; c=relate.connect(sys.argv[1]); "
                'print("SECOND_WRITER_OPENED"); c.close()',
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
    finally:
        owner.close()
    assert contender.returncode != 0 and "SECOND_WRITER_OPENED" not in contender.stdout
    assert "storage locked" in contender.stderr
    return contender.returncode


def main(action):
    if action == "seed":
        assert not DATA.exists() and not BACKUP.exists() and not EXPECTED.exists(), (
            "volumes must be new"
        )
        catalog = json.loads((ROOT / "catalog.json").read_text())
        counts = build_graph(catalog, DATA)
        expected = snapshot(DATA)
        shutil.copy2(DATA, BACKUP)
        EXPECTED.write_text(json.dumps(expected, ensure_ascii=False, sort_keys=True))
        print(
            json.dumps(
                {
                    "action": action,
                    "counts": counts,
                    "data_bytes": DATA.stat().st_size,
                    "backup_bytes": BACKUP.stat().st_size,
                }
            )
        )
    elif action == "verify":
        expected = json.loads(EXPECTED.read_text())
        assert snapshot(DATA) == expected
        lock_exit = check_writer_lock(DATA)
        assert snapshot(DATA) == expected
        print(
            json.dumps(
                {
                    "action": action,
                    "snapshot_equal": True,
                    "second_writer_exit": lock_exit,
                    "evidence_revision": expected["evidence"][0]["revision"],
                }
            )
        )
    elif action == "restore":
        assert not RESTORED.exists(), "restore volume must be new"
        shutil.copy2(BACKUP, RESTORED)
        assert snapshot(RESTORED) == json.loads(EXPECTED.read_text())
        print(
            json.dumps(
                {
                    "action": action,
                    "snapshot_equal": True,
                    "restored_bytes": RESTORED.stat().st_size,
                }
            )
        )
    else:
        raise SystemExit("usage: container_probe.py seed|verify|restore")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) == 2 else "")
