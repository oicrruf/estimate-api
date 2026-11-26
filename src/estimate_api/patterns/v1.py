"""Expansión acotada de patrones versionados; no valida diseño eléctrico."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, TypedDict, TypeGuard

from estimate_api.hardware.evaluate import evaluate_route
from estimate_api.knowledge.registry_v1 import InstallationPattern

PATTERN_VERSION = "1.0.0"


class Fact(TypedDict):
    state: Literal["confirmed", "assumed", "unknown"]
    value: str | bool | int | None
    evidenceId: str | None


class Condition(TypedDict):
    fact: str
    equals: str | bool | int


class Dependency(TypedDict):
    id: str
    fromId: str
    toId: str
    ruleId: str
    sourceRef: str
    condition: Condition | None
    quantityFact: str | None


class Pattern(TypedDict):
    id: str
    version: str
    category: str
    rootId: str
    sourceRef: str
    maxDepth: int
    maxEdges: int
    dependencies: list[Dependency]


class DraftCandidate(TypedDict):
    """Seam para AT-240: candidato, nunca línea seleccionada de BOM."""

    itemId: str
    quantity: int
    ruleIds: list[str]
    sourceRefs: list[str]
    evidenceIds: list[str]
    paths: list[list[str]]


@dataclass(frozen=True)
class Expansion:
    status: Literal["DERIVED", "PENDING", "LIMIT_REACHED"]
    candidates: tuple[DraftCandidate, ...]
    pending: tuple[str, ...]
    cycles: tuple[tuple[str, ...], ...]
    visited_edges: int
    professional_validation_required: bool = True


def registry_reference(pattern: Pattern) -> InstallationPattern:
    """El formato de referencia ya definido por AT-265."""
    return {"id": pattern["id"], "category": pattern["category"], "ref": pattern["sourceRef"]}


def _confirmed(fact: Fact | None) -> TypeGuard[Fact]:
    return fact is not None and fact["state"] == "confirmed" and bool(fact["evidenceId"])


def expand(pattern: Pattern, facts: dict[str, Fact]) -> Expansion:
    if pattern["version"] != PATTERN_VERSION or pattern["maxDepth"] < 1 or pattern["maxEdges"] < 1:
        raise ValueError("versión o límites de patrón inválidos")
    if len({edge["id"] for edge in pattern["dependencies"]}) != len(pattern["dependencies"]):
        raise ValueError("IDs de relaciones duplicados")
    if not _confirmed(facts.get("application")) or facts["application"]["value"] is not True:
        return Expansion("PENDING", (), ("application",), (), 0)
    by_origin: dict[str, list[Dependency]] = {}
    for edge in pattern["dependencies"]:
        by_origin.setdefault(edge["fromId"], []).append(edge)
    for edges in by_origin.values():
        edges.sort(key=lambda edge: edge["id"])
    result: dict[str, DraftCandidate] = {}
    quantity_conflicts: set[str] = set()
    pending: set[str] = set()
    cycles: set[tuple[str, ...]] = set()
    visited = 0
    limited = False
    stack: list[tuple[str, tuple[str, ...], int, tuple[str, ...]]] = [
        (pattern["rootId"], (pattern["rootId"],), 0, (str(facts["application"]["evidenceId"]),))
    ]
    while stack:
        origin, path, depth, inherited_evidence = stack.pop()
        edges = by_origin.get(origin, [])
        if depth >= pattern["maxDepth"]:
            if edges:
                limited = True
            continue
        for edge in edges:
            if visited >= pattern["maxEdges"]:
                limited = True
                break
            visited += 1
            condition = edge["condition"]
            evidence = list(inherited_evidence)
            if condition is not None:
                fact = facts.get(condition["fact"])
                if not _confirmed(fact):
                    pending.add(condition["fact"])
                    continue
                if (
                    type(fact["value"]) is not type(condition["equals"])
                    or fact["value"] != condition["equals"]
                ):
                    continue
                evidence.append(str(fact["evidenceId"]))
            quantity = 1
            if edge["quantityFact"] is not None:
                key = edge["quantityFact"]
                fact = facts.get(key)
                if not _confirmed(fact) or type(fact["value"]) is not int or fact["value"] < 0:
                    pending.add(key)
                    continue
                quantity = fact["value"]
                evidence.append(str(fact["evidenceId"]))
            target = edge["toId"]
            next_path = (*path, target)
            if target in path:
                cycles.add(next_path)
                continue
            if quantity == 0:
                continue
            if target in quantity_conflicts:
                continue
            existing = result.get(target)
            if existing is None:
                result[target] = {
                    "itemId": target,
                    "quantity": quantity,
                    "ruleIds": [edge["ruleId"]],
                    "sourceRefs": [edge["sourceRef"]],
                    "evidenceIds": sorted(set(evidence)),
                    "paths": [list(next_path)],
                }
            else:
                # Idempotent dependency: a second graph path is provenance, not a second item.
                if existing["quantity"] != quantity:
                    pending.add(f"quantity_conflict:{target}")
                    quantity_conflicts.add(target)
                    del result[target]
                    continue
                existing["ruleIds"] = sorted(set([*existing["ruleIds"], edge["ruleId"]]))
                existing["sourceRefs"] = sorted(set([*existing["sourceRefs"], edge["sourceRef"]]))
                existing["evidenceIds"] = sorted(set([*existing["evidenceIds"], *evidence]))
                if list(next_path) not in existing["paths"]:
                    existing["paths"].append(list(next_path))
            stack.append((target, next_path, depth + 1, tuple(sorted(set(evidence)))))
    return Expansion(
        "LIMIT_REACHED" if limited else "PENDING" if pending else "DERIVED",
        () if limited or quantity_conflicts else tuple(result[key] for key in sorted(result)),
        tuple(sorted(pending)),
        tuple(sorted(cycles)),
        visited,
    )


def evaluate_emt_with_at238(
    pattern: Pattern, facts: dict[str, Fact], catalog: dict[str, Any], route: dict[str, Any]
) -> tuple[Expansion, dict[str, Any] | None]:
    """Invoca AT-238 sólo para una ruta confirmada con la misma evidencia."""
    if pattern["id"] != "at247:pattern:emt-route":
        raise ValueError("se requiere el patrón EMT")
    expansion = expand(pattern, facts)
    measured = facts.get("route_measured")
    if (
        not any(c["itemId"] == "at247:item:at238-route-evaluation" for c in expansion.candidates)
        or expansion.status == "LIMIT_REACHED"
        or not _confirmed(measured)
        or measured["value"] is not True
        or route.get("confirmed") is not True
        or route.get("evidenceId") != measured["evidenceId"]
        or not _route_option_matches(
            facts, route, "lb_required", "lb_points", "lbRequired", "confirmedLbPoints"
        )
        or not _route_option_matches(
            facts,
            route,
            "interior_outlet_required",
            "outlet_points",
            "interiorOutletRequired",
            "confirmedOutletPoints",
        )
    ):
        return expansion, None
    return expansion, evaluate_route(catalog, route)


def _route_option_matches(
    facts: dict[str, Fact],
    route: dict[str, Any],
    condition_key: str,
    count_key: str,
    route_condition_key: str,
    route_count_key: str,
) -> bool:
    condition = facts.get(condition_key)
    route_enabled = route.get(route_condition_key) is True
    if _confirmed(condition) and condition["value"] is True and not route_enabled:
        return False
    if not route_enabled:
        return True
    count = facts.get(count_key)
    return (
        _confirmed(condition)
        and condition["value"] is True
        and _confirmed(count)
        and type(count["value"]) is int
        and count["value"] >= 0
        and route.get(route_count_key) == count["value"]
    )
