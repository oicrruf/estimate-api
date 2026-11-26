"""Seed idempotente de patrones sintéticos en un archivo Relate local."""

from __future__ import annotations

import json
from typing import Any

from estimate_api.patterns.v1 import Pattern


def _literal(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def seed_patterns(connection: Any, patterns: list[Pattern]) -> None:
    """MERGE por IDs AT-247; conserva nodos y relaciones ajenos."""
    for label in ("INSTALLATION_PATTERN", "PATTERN_ITEM", "PATTERN_RULE", "PATTERN_SOURCE"):
        connection.execute(
            f"CREATE CONSTRAINT at247_{label.lower()}_id IF NOT EXISTS "
            f"FOR (n:{label}) REQUIRE n.id IS UNIQUE"
        )
    for pattern in patterns:
        source = pattern["sourceRef"]
        connection.execute(
            f"MERGE (n:PATTERN_SOURCE {{id: {_literal(source)}}}) SET n.kind = 'synthetic_fixture'"
        )
        connection.execute(
            f"MERGE (n:INSTALLATION_PATTERN {{id: {_literal(pattern['id'])}}}) "
            f"SET n.version = {_literal(pattern['version'])}, "
            f"n.category = {_literal(pattern['category'])}"
        )
        connection.execute(f"MERGE (n:PATTERN_ITEM {{id: {_literal(pattern['rootId'])}}})")
        connection.execute(
            f"MATCH (a:INSTALLATION_PATTERN {{id: {_literal(pattern['id'])}}}), "
            f"(b:PATTERN_ITEM {{id: {_literal(pattern['rootId'])}}}) "
            f"MERGE (a)-[:HAS_ROOT]->(b)"
        )
        for edge in pattern["dependencies"]:
            for item_id in (edge["fromId"], edge["toId"]):
                connection.execute(f"MERGE (n:PATTERN_ITEM {{id: {_literal(item_id)}}})")
            connection.execute(f"MERGE (n:PATTERN_RULE {{id: {_literal(edge['ruleId'])}}})")
            connection.execute(
                f"MATCH (a:PATTERN_ITEM {{id: {_literal(edge['fromId'])}}}), "
                f"(b:PATTERN_ITEM {{id: {_literal(edge['toId'])}}}) "
                f"MERGE (a)-[r:PATTERN_REQUIRES {{id: {_literal(edge['id'])}}}]->(b) "
                f"SET r.ruleId = {_literal(edge['ruleId'])}, "
                f"r.condition = {_literal(json.dumps(edge['condition'], sort_keys=True))}"
            )
            connection.execute(
                f"MATCH (a:PATTERN_RULE {{id: {_literal(edge['ruleId'])}}}), "
                f"(b:PATTERN_SOURCE {{id: {_literal(edge['sourceRef'])}}}) "
                f"MERGE (a)-[:SUPPORTED_BY]->(b)"
            )
            connection.execute(
                f"MATCH (a:INSTALLATION_PATTERN {{id: {_literal(pattern['id'])}}}), "
                f"(b:PATTERN_RULE {{id: {_literal(edge['ruleId'])}}}) "
                f"MERGE (a)-[:USES_RULE]->(b)"
            )
