#!/usr/bin/env python3
"""Verifica fixtures sintéticos en relate-db 1.3.0, sin servicio ni credenciales."""

import json
import tempfile
from pathlib import Path

import relate

BASE = Path(__file__).resolve().parent
EXPECTED = json.loads((BASE / "expected.json").read_text(encoding="utf-8"))


def statements(name):
    # Las líneas de comentario se retiran antes de separar por ';'.
    source = "\n".join(
        line
        for line in (BASE / name).read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("//")
    )
    return [query.strip() for query in source.split(";") if query.strip()]


def counts(conn):
    nodes = conn.execute("MATCH (n) RETURN count(n) AS n").single()["n"]
    edges = conn.execute("MATCH ()-[r]->() RETURN count(r) AS n").single()["n"]
    return nodes, edges


def check_row(actual, expected):
    for key, value in expected.items():
        if key == "evidenceEnd":
            assert any(path["nodes"][-1] == value for path in actual["evidencePaths"]), (
                key,
                value,
                actual,
            )
        elif key == "offerIds":
            assert sorted(actual[key]) == sorted(value), (key, value, actual[key])
        else:
            assert actual[key] == value, (key, value, actual.get(key))
    for path in actual.get("evidencePaths", []):
        assert len(path["nodes"]) == len(path["relations"]) + 1, path


def main():
    seed = statements("seed.cypher")
    queries = statements("queries.cypher")
    assert len(queries) == 9, len(queries)
    with tempfile.TemporaryDirectory(prefix="at229-relate-") as directory:
        db_path = str(Path(directory) / "evidence.db")
        conn = relate.connect(db_path)
        for query in seed:
            conn.execute(query)
        first = counts(conn)
        assert first == (60, 61), first
        conn.close()

        conn = relate.connect(db_path)
        assert counts(conn) == first, "No persistió tras reapertura"
        for query in seed:
            conn.execute(query)
        assert counts(conn) == first, "El seed no fue idempotente"
        for number, query in enumerate(queries, 1):
            rows = conn.execute(query).data()
            expected = EXPECTED[f"Q{number}"]
            expected_rows = expected if isinstance(expected, list) else [expected]
            assert len(rows) == len(expected_rows), (number, rows)
            by_product = {row["productId"]: row for row in rows}
            for item in expected_rows:
                check_row(by_product[item["productId"]], item)
            print(f"Q{number}: OK ({len(rows)} fila{'s' if len(rows) != 1 else ''})")
        conn.close()

        conn = relate.connect(db_path)
        assert counts(conn) == first, "Cambió tras segunda reapertura"
        conn.close()
    print(
        f"Relate {getattr(relate, '__version__', '1.3.0')}: OK; "
        f"{first[0]} nodos, {first[1]} relaciones; seed x2; reapertura x2"
    )


if __name__ == "__main__":
    main()
