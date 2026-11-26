#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
spike="$root/spikes/relate"
project="at215_probe_$$"
venv="$(mktemp -d)"

cleanup() {
  docker compose -p "$project" -f "$spike/compose.yaml" down -v >/dev/null 2>&1 || true
  docker image rm "${project}-probe" >/dev/null 2>&1 || true
  rm -rf "$venv" "$spike/wheelhouse"
}

test ! -e "$spike/wheelhouse"
trap cleanup EXIT
python3 -m venv "$venv"
"$venv/bin/python" -m pip install --only-binary=:all: --require-hashes -r "$spike/requirements-container.txt"
"$venv/bin/python" "$spike/spike.py" > "$venv/python-result.json"
"$venv/bin/python" - "$venv/python-result.json" <<'PY'
import json, sys
r = json.load(open(sys.argv[1]))
assert r['reopen_equal'] and r['fresh_process_equal'] and r['rebuild_equal']
assert r['second_writer_exit'] == 1
print('Python/Cypher: reopen, fresh process, rebuild, writer lock PASS')
PY

mkdir "$spike/wheelhouse"
"$venv/bin/python" -m pip download --only-binary=:all: --no-deps --dest "$spike/wheelhouse" relate-db==1.3.0
printf '%s\n' '33ba7a6163d3bc2f2220a7ac3719754b091735071ce48c54489978fbacc9d1b4  wheelhouse/relate_db-1.3.0-cp39-abi3-manylinux2014_x86_64.manylinux_2_17_x86_64.whl' | (cd "$spike" && sha256sum -c -)
docker compose -p "$project" -f "$spike/compose.yaml" build
docker compose -p "$project" -f "$spike/compose.yaml" run --rm probe seed
docker compose -p "$project" -f "$spike/compose.yaml" run --rm probe verify
docker compose -p "$project" -f "$spike/compose.yaml" run --rm probe restore
