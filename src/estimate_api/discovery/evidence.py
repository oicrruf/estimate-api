"""Read-only, bounded lookup of AT-229 graph evidence references.

An evidence node supports a product capability. It does not validate an
installation dependency rule or a commercial product choice.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

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
_PATTERN_RULES = (
    "MATCH (p:INSTALLATION_PATTERN)-[:USES_RULE]->(r:PATTERN_RULE)"
    "-[:SUPPORTED_BY]->(s:PATTERN_SOURCE) "
    "RETURN p.id AS patternId, r.id AS ruleId, s.id AS sourceRef "
    "ORDER BY p.id, r.id LIMIT 500"
)
_TOPOLOGY_LINKS = (
    "MATCH (e:ENDPOINT)-[:REQUIRES_LINK]->(l:NETWORK_LINK)-[:SUPPORTED_BY]->(v:EVIDENCE) "
    "RETURN e.id AS endpointId, l.id AS linkId, l.datasetId AS datasetId, "
    "v.id AS evidenceId ORDER BY l.id LIMIT 200"
)


class Result(Protocol):
    def data(self) -> Sequence[Mapping[str, Any]]: ...


class ReadConnection(Protocol):
    def execute(self, query: str, params: dict[str, Any] | None = None) -> Result: ...


@dataclass(frozen=True)
class EvidenceReference:
    id: str
    status: str
    source: str | None
    capability_paths: tuple[tuple[str, str, str], ...]


@dataclass(frozen=True)
class PatternRuleReference:
    pattern_id: str
    rule_id: str
    source_ref: str | None
    status: str


@dataclass(frozen=True)
class TopologyLinkReference:
    link_id: str
    endpoint_id: str | None
    evidence_id: str | None
    status: str


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

    def resolve_pattern_rules(
        self, pattern_id: str, rule_ids: tuple[str, ...]
    ) -> tuple[PatternRuleReference, ...]:
        if not pattern_id or len(rule_ids) > 100 or len(set(rule_ids)) != len(rule_ids):
            raise ValueError("Invalid pattern rule lookup")
        rows = self.connection.execute(_PATTERN_RULES).data()
        indexed = {(row.get("patternId"), row.get("ruleId")): row.get("sourceRef") for row in rows}
        return tuple(
            PatternRuleReference(
                pattern_id,
                rule_id,
                str(indexed[(pattern_id, rule_id)])
                if indexed.get((pattern_id, rule_id)) is not None
                else None,
                "rule_context" if (pattern_id, rule_id) in indexed else "unknown",
            )
            for rule_id in rule_ids
        )

    def resolve_topology_links(
        self, link_ids: tuple[str, ...], dataset_id: str
    ) -> tuple[TopologyLinkReference, ...]:
        if not dataset_id or len(link_ids) > 100 or len(set(link_ids)) != len(link_ids):
            raise ValueError("Invalid topology lookup")
        rows = self.connection.execute(_TOPOLOGY_LINKS).data()
        indexed = {row.get("linkId"): row for row in rows if row.get("datasetId") == dataset_id}
        return tuple(
            TopologyLinkReference(
                link_id,
                str(indexed[link_id]["endpointId"]) if link_id in indexed else None,
                str(indexed[link_id]["evidenceId"]) if link_id in indexed else None,
                "required_link_context" if link_id in indexed else "unknown",
            )
            for link_id in link_ids
        )
