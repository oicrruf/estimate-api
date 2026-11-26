"""Read-only, bounded lookup of AT-229 graph evidence references.

An evidence node supports a product capability. It does not validate an
installation dependency rule or a commercial product choice.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

_NODES = (
    "MATCH (e:EVIDENCE) WHERE e.id IN $ids AND e.datasetId = $dataset "
    "RETURN e.id AS id, e.source AS source, e.datasetId AS datasetId "
    "ORDER BY e.id, e.source SKIP $offset LIMIT $limit"
)
_PATHS = (
    "MATCH (p:PRODUCT)-[:SUPPORTS]->(c:CAPABILITY)-[:SUPPORTED_BY]->(e:EVIDENCE) "
    "WHERE e.id IN $ids AND e.datasetId = $dataset "
    "RETURN p.id AS productId, c.id AS capabilityId, c.key AS capabilityKey, "
    "e.id AS evidenceId ORDER BY e.id, p.id, c.id SKIP $offset LIMIT $limit"
)
_PATTERN_RULES = (
    "MATCH (p:INSTALLATION_PATTERN)-[:USES_RULE]->(r:PATTERN_RULE)"
    "-[:SUPPORTED_BY]->(s:PATTERN_SOURCE) "
    "WHERE p.id = $pattern AND r.id IN $ids "
    "RETURN p.id AS patternId, r.id AS ruleId, s.id AS sourceRef "
    "ORDER BY p.id, r.id, s.id SKIP $offset LIMIT $limit"
)
_TOPOLOGY_LINKS = (
    "MATCH (e:ENDPOINT)-[:REQUIRES_LINK]->(l:NETWORK_LINK)-[:SUPPORTED_BY]->(v:EVIDENCE) "
    "WHERE l.id IN $ids AND e.datasetId = $dataset "
    "AND l.datasetId = $dataset AND v.datasetId = $dataset "
    "RETURN e.id AS endpointId, l.id AS linkId, l.datasetId AS datasetId, "
    "v.id AS evidenceId ORDER BY l.id, e.id, v.id SKIP $offset LIMIT $limit"
)

_PAGE_SIZE = 200


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

    def _pages(self, query: str, params: dict[str, Any]) -> tuple[Mapping[str, Any], ...]:
        """Page only the requested, parameterized graph subset."""
        rows: list[Mapping[str, Any]] = []
        offset = 0
        while True:
            batch = self.connection.execute(
                query, {**params, "offset": offset, "limit": _PAGE_SIZE}
            ).data()
            rows.extend(batch)
            if len(batch) < _PAGE_SIZE:
                return tuple(rows)
            offset += _PAGE_SIZE

    def resolve(self, evidence_ids: tuple[str, ...]) -> tuple[EvidenceReference, ...]:
        if len(evidence_ids) > 100 or len(set(evidence_ids)) != len(evidence_ids):
            raise ValueError("Evidence reference limit or duplicate")
        if not evidence_ids:
            return ()
        params = {"ids": list(evidence_ids), "dataset": self.dataset_id}
        nodes = self._pages(_NODES, params)
        paths = self._pages(_PATHS, params)
        by_id: dict[str, Mapping[str, Any]] = {}
        for row in nodes:
            identifier = row.get("id")
            if not isinstance(identifier, str) or identifier in by_id:
                raise ValueError("Ambiguous evidence node in requested dataset")
            by_id[identifier] = row
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
        if not rule_ids:
            return ()
        rows = self._pages(_PATTERN_RULES, {"pattern": pattern_id, "ids": list(rule_ids)})
        indexed: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
        for row in rows:
            key = (str(row.get("patternId")), str(row.get("ruleId")))
            indexed.setdefault(key, []).append(row)
        return tuple(
            PatternRuleReference(
                pattern_id,
                rule_id,
                str(row["sourceRef"]) if row is not None else None,
                "rule_context" if row is not None else "unknown",
            )
            for rule_id in rule_ids
            for row in indexed.get((pattern_id, rule_id), [None])
        )

    def resolve_topology_links(
        self, link_ids: tuple[str, ...], dataset_id: str
    ) -> tuple[TopologyLinkReference, ...]:
        if not dataset_id or len(link_ids) > 100 or len(set(link_ids)) != len(link_ids):
            raise ValueError("Invalid topology lookup")
        if not link_ids:
            return ()
        rows = self._pages(_TOPOLOGY_LINKS, {"ids": list(link_ids), "dataset": dataset_id})
        indexed: dict[str, list[Mapping[str, Any]]] = {}
        for row in rows:
            key = str(row.get("linkId"))
            indexed.setdefault(key, []).append(row)
        return tuple(
            TopologyLinkReference(
                link_id,
                str(row["endpointId"]) if row is not None else None,
                str(row["evidenceId"]) if row is not None else None,
                "required_link_context" if row is not None else "unknown",
            )
            for link_id in link_ids
            for row in indexed.get(link_id, [None])
        )
