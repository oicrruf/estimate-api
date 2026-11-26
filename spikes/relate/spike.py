"""Disposable Relate runtime probe with synthetic catalog data only."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import relate

ROOT = Path(__file__).resolve().parent


def rows(conn, query, params=None):
    return [dict(row) for row in conn.execute(query, params or {})]


def build_graph(catalog, path):
    conn = relate.connect(str(path))
    try:
        for item in catalog["products"]:
            conn.execute("CREATE (:Product {id: $id, name: $name})", item)
        for item in catalog["capabilities"]:
            conn.execute("CREATE (:Capability {id: $id, name: $name})", item)
        for item in catalog["evidence"]:
            conn.execute("CREATE (:Evidence {id: $id, revision: $revision, claim: $claim})", item)
        for item in catalog["evidence_revisions"]:
            conn.execute(
                "MATCH (e:Evidence {id: $evidence}) "
                "CREATE (e)-[:HAS_REVISION]->(:EvidenceRevision "
                "{id: $id, revision: $revision, claim: $claim, reason: $reason})",
                item,
            )
        for item in catalog["projects"]:
            conn.execute("CREATE (:Project {id: $id})", item)
        for item in catalog["requirements"]:
            conn.execute(
                "MATCH (p:Project {id: $project}), (c:Capability {id: $capability}) "
                "CREATE (r:Requirement {id: $id})-[:FOR_PROJECT]->(p), "
                "(r)-[:NEEDS]->(c)",
                item,
            )
        for item in catalog["product_capabilities"]:
            conn.execute(
                "MATCH (p:Product {id: $product}), (c:Capability {id: $capability}), "
                "(e:Evidence {id: $evidence}) "
                "CREATE (p)-[:HAS_CAPABILITY {evidence_id: $evidence}]->(c), "
                "(e)-[:SUPPORTS]->(c)",
                item,
            )
        for item in catalog["compatibilities"]:
            conn.execute(
                "MATCH (a:Product {id: $from}), (b:Product {id: $to}) "
                "CREATE (a)-[:COMPATIBLE_WITH {status: $status}]->(b)",
                item,
            )
        for item in catalog["alternatives"]:
            conn.execute(
                "MATCH (a:Product {id: $from}), (b:Product {id: $to}) "
                "CREATE (a)-[:ALTERNATIVE_TO]->(b)",
                item,
            )
        for item in catalog["candidates"]:
            conn.execute(
                "MATCH (p:Project {id: $project}), (x:Product {id: $product}) "
                "CREATE (p)-[:CANDIDATE {status: $status}]->(x)",
                item,
            )
        return {
            label: rows(conn, f"MATCH (n:{label}) RETURN count(n) AS count")[0]["count"]
            for label in (
                "Product",
                "Capability",
                "Evidence",
                "EvidenceRevision",
                "Project",
                "Requirement",
            )
        }
    finally:
        conn.close()


QUERIES = {
    "capabilities": (
        "MATCH (p:Product)-[:HAS_CAPABILITY]->(c:Capability) "
        "RETURN p.id AS product, c.id AS capability ORDER BY product, capability"
    ),
    "evidence": (
        "MATCH (e:Evidence {id: 'ev:datasheet-a'}) "
        "RETURN e.id AS id, e.revision AS revision, e.claim AS claim"
    ),
    "evidence_history": (
        "MATCH (e:Evidence)-[:HAS_REVISION]->(r:EvidenceRevision) "
        "RETURN e.id AS evidence, r.id AS revision_id, r.revision AS revision, "
        "r.claim AS claim, r.reason AS reason ORDER BY revision"
    ),
    "compatibility": (
        "MATCH (a:Product)-[r:COMPATIBLE_WITH]->(b:Product) "
        "RETURN a.id AS source, b.id AS target, r.status AS status"
    ),
    "alternatives": (
        "MATCH (a:Product)-[:ALTERNATIVE_TO]->(b:Product) RETURN a.id AS source, b.id AS target"
    ),
    "requirements": (
        "MATCH (r:Requirement)-[:FOR_PROJECT]->(p:Project), "
        "(r)-[:NEEDS]->(c:Capability) "
        "RETURN r.id AS requirement, p.id AS project, c.id AS capability"
    ),
    "candidates": (
        "MATCH (p:Project)-[r:CANDIDATE]->(x:Product) "
        "RETURN p.id AS project, x.id AS product, r.status AS status ORDER BY project"
    ),
    "eligible_north": (
        "MATCH (p:Project {id: 'project:north'})-[r:CANDIDATE]->(x:Product) "
        "WHERE r.status = 'eligible' RETURN x.id AS product"
    ),
    "eligible_south": (
        "MATCH (p:Project {id: 'project:south'})-[r:CANDIDATE]->(x:Product) "
        "WHERE r.status = 'eligible' RETURN x.id AS product"
    ),
}


def snapshot(path):
    conn = relate.connect(str(path))
    try:
        return {name: rows(conn, query) for name, query in QUERIES.items()}
    finally:
        conn.close()


def main():
    catalog = json.loads((ROOT / "catalog.json").read_text())
    with tempfile.TemporaryDirectory(prefix="relate-spike-") as temp:
        store = Path(temp) / "catalog.rl"
        counts = build_graph(catalog, store)
        first = snapshot(store)
        owner = relate.connect(str(store))
        try:
            attempt = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "import relate,sys; c=relate.connect(sys.argv[1]); "
                    "print('SECOND_WRITER_OPENED'); c.close()",
                    str(store),
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )
        finally:
            owner.close()
        assert attempt.returncode != 0 and "SECOND_WRITER_OPENED" not in attempt.stdout, attempt
        reopened = snapshot(store)
        assert reopened == first
        fresh = subprocess.run(
            [sys.executable, __file__, "snapshot", str(store)],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
        assert json.loads(fresh.stdout) == first
        assert first["eligible_north"] == []
        assert first["eligible_south"] == [{"product": "prod:solar-a"}]
        assert first["evidence"][0]["revision"] == 2
        assert [x["revision"] for x in first["evidence_history"]] == [1, 2]
        assert first["compatibility"] and first["alternatives"] and first["requirements"]
        rebuilt_store = Path(temp) / "rebuilt.rl"
        rebuilt_counts = build_graph(catalog, rebuilt_store)
        assert snapshot(rebuilt_store) == first and rebuilt_counts == counts
        print(
            json.dumps(
                {
                    "python": sys.version.split()[0],
                    "relate": relate.__version__,
                    "store_bytes": store.stat().st_size,
                    "counts": counts,
                    "queries": first,
                    "second_writer_exit": attempt.returncode,
                    "second_writer_error": attempt.stderr.strip().splitlines()[-1],
                    "reopen_equal": True,
                    "fresh_process_equal": True,
                    "rebuild_equal": True,
                },
                ensure_ascii=False,
                indent=2,
            )
        )


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "snapshot":
        print(json.dumps(snapshot(Path(sys.argv[2])), ensure_ascii=False))
    else:
        main()
