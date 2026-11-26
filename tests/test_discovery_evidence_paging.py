"""Relate evidence lookups filter before paging a synthetic local graph."""

import tempfile
from pathlib import Path

import pytest
import relate

from estimate_api.discovery.evidence import RelateEvidenceReader


def test_requested_evidence_is_found_after_global_node_and_path_prefixes() -> None:
    with tempfile.TemporaryDirectory(prefix="at240-evidence-pages-") as directory:
        connection = relate.connect(str(Path(directory) / "evidence.db"))
        for index in range(201):
            evidence = f"EV-{index:03}"
            paths = ", ".join(
                f"(p)-[:SUPPORTS]->(c{part}:CAPABILITY {{id:'C-{index:03}-{part}', "
                f"key:'key-{part}'}})-[:SUPPORTED_BY]->(e)"
                for part in range(1, 4)
            )
            connection.execute(
                f"CREATE (p:PRODUCT {{id:'P-{index:03}'}})"
                f"-[:SUPPORTS]->(c0:CAPABILITY {{id:'C-{index:03}-0'}})"
                f"-[:SUPPORTED_BY]->(e:EVIDENCE {{id:'{evidence}', "
                "datasetId:'synthetic-v1', source:'earlier'}), "
                f"{paths}"
            )
        target_paths = ", ".join(
            f"(p)-[:SUPPORTS]->(c{part}:CAPABILITY {{id:'ZZ-C-{part:03}', "
            f"key:'target-{part:03}'}})-[:SUPPORTED_BY]->(e)"
            for part in range(1, 205)
        )
        connection.execute(
            "CREATE (p:PRODUCT {id:'ZZ-P'})"
            "-[:SUPPORTS]->(c0:CAPABILITY {id:'ZZ-C-000', key:'target-000'})"
            "-[:SUPPORTED_BY]->(e:EVIDENCE {id:'ZZ-TARGET', "
            "datasetId:'synthetic-v1', source:'correct'}), "
            f"{target_paths}"
        )
        connection.execute(
            "CREATE (p:PRODUCT {id:'ZZ-FOREIGN'})"
            "-[:SUPPORTS]->(c:CAPABILITY {id:'ZZ-FOREIGN-C'})"
            "-[:SUPPORTED_BY]->(e:EVIDENCE {id:'ZZ-TARGET', "
            "datasetId:'foreign-v1', source:'wrong'})"
        )
        before = connection.execute("MATCH (n) RETURN count(n) AS n").single()["n"]
        reader = RelateEvidenceReader(connection, "synthetic-v1")
        found, missing = reader.resolve(("ZZ-TARGET", "ZZ-MISSING"))
        assert found.id == "ZZ-TARGET" and found.source == "correct"
        assert found.status == "capability_context"
        assert len(found.capability_paths) == 205
        assert found.capability_paths[0] == ("ZZ-P", "ZZ-C-000", "ZZ-TARGET")
        assert found.capability_paths[-1] == ("ZZ-P", "ZZ-C-204", "ZZ-TARGET")
        assert missing.id == "ZZ-MISSING" and missing.status == "unknown"
        with pytest.raises(ValueError, match="duplicate"):
            reader.resolve(("ZZ-TARGET", "ZZ-TARGET"))
        assert connection.execute("MATCH (n) RETURN count(n) AS n").single()["n"] == before
        connection.execute(
            "CREATE (:EVIDENCE {id:'ZZ-TARGET', datasetId:'synthetic-v1', source:'ambiguous'})"
        )
        with pytest.raises(ValueError, match="Ambiguous evidence node"):
            reader.resolve(("ZZ-TARGET",))
        connection.close()


def test_pattern_and_topology_paths_filter_before_their_old_global_limits() -> None:
    with tempfile.TemporaryDirectory(prefix="at240-path-pages-") as directory:
        connection = relate.connect(str(Path(directory) / "paths.db"))
        for index in range(501):
            connection.execute(
                f"CREATE (p:INSTALLATION_PATTERN {{id:'P-{index:03}'}})"
                f"-[:USES_RULE]->(r:PATTERN_RULE {{id:'R-{index:03}'}})"
                f"-[:SUPPORTED_BY]->(s:PATTERN_SOURCE {{id:'S-{index:03}'}})"
            )
        for index in range(201):
            connection.execute(
                f"CREATE (e:ENDPOINT {{id:'E-{index:03}', datasetId:'synthetic-v1'}})"
                f"-[:REQUIRES_LINK]->(l:NETWORK_LINK {{id:'L-{index:03}', "
                "datasetId:'synthetic-v1'})"
                f"-[:SUPPORTED_BY]->(v:EVIDENCE {{id:'V-{index:03}', "
                "datasetId:'synthetic-v1'})"
            )
        connection.execute(
            "MATCH (r:PATTERN_RULE {id:'R-500'}) "
            "CREATE (r)-[:SUPPORTED_BY]->(s:PATTERN_SOURCE {id:'S-500-B'})"
        )
        connection.execute(
            "MATCH (l:NETWORK_LINK {id:'L-200'}) "
            "CREATE (l)-[:SUPPORTED_BY]->(v:EVIDENCE {id:'V-200-B', "
            "datasetId:'synthetic-v1'})"
        )
        reader = RelateEvidenceReader(connection, "synthetic-v1")
        rules = reader.resolve_pattern_rules("P-500", ("R-500",))
        assert [item.source_ref for item in rules] == ["S-500", "S-500-B"]
        assert all(item.status == "rule_context" for item in rules)
        links = reader.resolve_topology_links(("L-200",), "synthetic-v1")
        assert [item.endpoint_id for item in links] == ["E-200", "E-200"]
        assert [item.evidence_id for item in links] == ["V-200", "V-200-B"]
        assert all(item.status == "required_link_context" for item in links)
        assert reader.resolve_topology_links(("L-200",), "foreign-v1")[0].status == "unknown"
        connection.close()
