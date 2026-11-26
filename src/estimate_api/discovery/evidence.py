"""Read-only, bounded lookup of AT-229 graph evidence references.

An evidence node supports a product capability. It does not validate an
installation dependency rule or a commercial product choice.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

_NODES = (
    "MATCH (e:EVIDENCE) "
    "RETURN e.id AS id, e.source AS source, e.datasetId AS datasetId "
    "ORDER BY e.id LIMIT 200"
)
_PATHS = (
    "MATCH (p:PRODUCT)-[:SUPPORTS]->(c:CAPABILITY)-[:SUPPORTED_BY]->(e:EVIDENCE) "
    "RETURN p.id AS productId, c.id AS capabilityId, c.key AS capabilityKey, "
    "e.id AS evidenceId ORDER BY p.id, c.id LIMIT 500"
)


class Result(Protocol):
    def data(self) -> list[dict[str, object]]: ...


class ReadConnection(Protocol):
    def execute(self, query: str) -> Result: ...


@dataclass(frozen=True)
class EvidenceReference:
    id: str
    status: str
    source: str | None
    capability_paths: tuple[tuple[str, str, str], ...]


class RelateEvidenceReader:
    """Uses only fixed MATCH/RETURN queries against a caller-owned connection."""

    def __init__(self, connection: ReadConnection, dataset_id: str) -> None:
        if not dataset_id:
            raise ValueError("Expected dataset ID is required")
        self.connection = connection
        self.dataset_id = dataset_id

    def resolve(self, evidence_ids: tuple[str, ...]) -> tuple[EvidenceReference, ...]:
        if len(evidence_ids) > 100 or len(set(evidence_ids)) != len(evidence_ids):
            raise ValueError("Evidence reference limit or duplicate")
        if not evidence_ids:
            return ()
        nodes = self.connection.execute(_NODES).data()
        paths = self.connection.execute(_PATHS).data()
        by_id = {
            row["id"]: row
            for row in nodes
            if row.get("datasetId") == self.dataset_id and isinstance(row.get("id"), str)
        }
        result = []
        for evidence_id in evidence_ids:
            node = by_id.get(evidence_id)
            related = (
                tuple(
                    (str(row["productId"]), str(row["capabilityId"]), evidence_id)
                    for row in paths
                    if row.get("evidenceId") == evidence_id
                )
                if node
                else ()
            )
            status = "capability_context" if related else "node_only" if node else "unknown"
            result.append(
                EvidenceReference(
                    evidence_id, status, str(node["source"]) if node else None, related
                )
            )
        return tuple(result)
