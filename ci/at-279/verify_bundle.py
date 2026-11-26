"""Reproduce and verify the private AT-278/279 tar without uploading it."""

from __future__ import annotations

import gzip
import hashlib
import io
import tarfile
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent / "package"
EXPECTED_SHA256 = "18fda4a6fdd3a167d7c95b76d6b3cb3c83fc06c593c58d3cc91425f2b4484e67"
EXCLUDED = {
    ".git",
    "node_modules",
    ".venv",
    "dist",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".angular",
}


def package_files() -> list[Path]:
    files: list[Path] = []
    for path in PACKAGE.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"Symlink unexpected: {path}")
        if not path.is_file():
            continue
        rel = path.relative_to(PACKAGE)
        if any(part in EXCLUDED or part.startswith(".env") for part in rel.parts):
            raise ValueError(f"Excluded file present: {rel}")
        if rel.name == "build-ca.pem" or rel.suffix in {".log", ".pem", ".key", ".rl"}:
            raise ValueError(f"Private/transient file present: {rel}")
        files.append(rel)
    return sorted(p for p in files if p != Path("MANIFEST.sha256")) + [Path("MANIFEST.sha256")]


def main() -> None:
    files = package_files()
    manifest_path = Path("MANIFEST.sha256")
    assert manifest_path in files
    manifest: dict[str, str] = {}
    for row in (PACKAGE / manifest_path).read_text().splitlines():
        checksum, name = row.split("  ", 1)
        if name in manifest:
            raise ValueError(f"Duplicate manifest entry: {name}")
        manifest[name] = checksum
    actual = {str(p) for p in files if p != manifest_path}
    if set(manifest) != actual:
        missing = actual - set(manifest)
        extra = set(manifest) - actual
        raise ValueError(f"Manifest mismatch: missing={missing}, extra={extra}")
    for name, checksum in manifest.items():
        if hashlib.sha256((PACKAGE / name).read_bytes()).hexdigest() != checksum:
            raise ValueError(f"Hash mismatch: {name}")

    output = io.BytesIO()
    with gzip.GzipFile(fileobj=output, mode="wb", filename="", mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode="w") as archive:
            for rel in files:
                archive_name = str(Path("estimate-agent-private-preview") / rel)
                info = archive.gettarinfo(str(PACKAGE / rel), arcname=archive_name)
                info.uid = info.gid = 0
                info.uname = info.gname = ""
                info.mtime = 0
                with (PACKAGE / rel).open("rb") as source:
                    archive.addfile(info, source)
    digest = hashlib.sha256(output.getvalue()).hexdigest()
    if digest != EXPECTED_SHA256:
        raise ValueError(f"Archive digest drift: {digest}")
    print(f"Paquete exacto: {len(files)} archivos, SHA256 {digest}")


if __name__ == "__main__":
    main()
