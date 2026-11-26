"""ADK y Relate locales para un único escenario sintético de BOM."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import AsyncGenerator
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any, cast

import relate
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.runners import InMemoryRunner
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types

from demo.agent.graph import _statements
from estimate_api.domain.scope_capture.contract import (
    Certainty,
    Measurement,
    ScopeIntake,
    build_scope_draft,
)
from estimate_api.domain.scope_capture.contract import (
    Fact as ScopeFact,
)
from estimate_api.ethernet.evaluate import evaluate_topology
from estimate_api.hardware.evaluate import evaluate_route
from estimate_api.patterns.v1 import Fact as PatternFact
from estimate_api.patterns.v1 import Pattern, expand

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = json.loads((Path(__file__).with_name("fixture.json")).read_text(encoding="utf-8"))
HARDWARE = json.loads((ROOT / "demo/hardware/fixture.json").read_text(encoding="utf-8"))
PATTERNS: list[Pattern] = json.loads(
    (ROOT / "fixtures/patterns/patterns.v1.json").read_text(encoding="utf-8")
)["patterns"]

ROUTE_QUERY = """
MATCH (s:INSTALLATION_SEGMENT {id:'SEG-DEMO'})-[r:REQUIRES]->(q:REQUIREMENT)
MATCH (q)-[:SUPPORTED_BY]->(e:EVIDENCE)
RETURN s.id AS routeId, q.id AS requirementId, q.family AS family,
       r.ruleId AS ruleId, e.id AS evidenceId ORDER BY requirementId
"""
MATERIAL_QUERY = """
MATCH (i:MATERIAL)-[:FITS_DIAMETER]->(d:SPEC), (i)-[:SUPPORTED_BY]->(e:EVIDENCE)
RETURN i.id AS itemId, i.family AS family, d.id AS specId,
       d.diameter AS diameter, e.id AS evidenceId ORDER BY itemId
"""
ACCESSORY_QUERY = """
MATCH (i:ACCESSORY)-[:FITS_DIAMETER]->(d:SPEC), (i)-[:SUPPORTED_BY]->(e:EVIDENCE)
RETURN i.id AS itemId, i.family AS family, d.id AS specId,
       d.diameter AS diameter, e.id AS evidenceId ORDER BY itemId
"""


def seed(store_path: Path) -> None:
    if not store_path.parent.is_dir():
        raise ValueError("El directorio del store debe existir")
    conn = relate.connect(str(store_path))
    try:
        count = conn.execute("MATCH (n) RETURN count(n) AS n").single()["n"]
        marker = conn.execute(
            "MATCH (s:INSTALLATION_SEGMENT {id:'SEG-DEMO'}) RETURN count(s) AS n"
        ).single()["n"]
        if count and not marker:
            raise ValueError("Store ajeno al fixture guiado")
        for statement in _statements(ROOT / "demo/hardware/seed.cypher"):
            conn.execute(statement)
        for statement in _statements(Path(__file__).with_name("seed_extra.cypher")):
            conn.execute(statement)
    finally:
        conn.close()


def graph_evidence(store_path: str) -> dict[str, list[dict[str, Any]]]:
    """Herramienta fija: consultas de lectura con rutas reales; sin Cypher de entrada."""
    if not Path(store_path).is_file():
        raise ValueError("Seed requerido")
    conn = relate.connect(store_path, read_only=True)
    try:
        return {
            "route": [dict(row) for row in conn.execute(ROUTE_QUERY)],
            "materials": [dict(row) for row in conn.execute(MATERIAL_QUERY)],
            "accessories": [dict(row) for row in conn.execute(ACCESSORY_QUERY)],
        }
    finally:
        conn.close()


def _fill(cable_count: int, cable_od_in: str | None, conduit_id_in: str) -> dict[str, Any]:
    # pi/4 cancels; the 40% cap is an illustrative fixture choice, not a code rule.
    if cable_od_in is None:
        return {
            "occupiedAreaFactorIn2": None,
            "allowedAreaFactorIn2": None,
            "fillPercent": None,
            "eligible": None,
        }
    occupied = Decimal(cable_count) * Decimal(cable_od_in) ** 2
    whole = Decimal(conduit_id_in) ** 2
    capacity = Decimal(FIXTURE["fillDemo"]["thresholdFraction"]) * whole
    return {
        "occupiedAreaFactorIn2": str(occupied),
        "allowedAreaFactorIn2": str(capacity),
        "fillPercent": str(
            (occupied / whole * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        ),
        "eligible": occupied <= capacity,
    }


def _path(row: dict[str, Any], item_type: str) -> list[dict[str, Any]]:
    return [
        {
            "nodes": [
                {"id": row["itemId"], "type": item_type},
                {"id": row["specId"], "type": "SPEC"},
            ],
            "relations": ["FITS_DIAMETER"],
        },
        {
            "nodes": [
                {"id": row["itemId"], "type": item_type},
                {"id": row["evidenceId"], "type": "EVIDENCE"},
            ],
            "relations": ["SUPPORTED_BY"],
        },
    ]


def _confirmed(value: str | bool | int, evidence: str) -> PatternFact:
    return {"state": "confirmed", "value": value, "evidenceId": evidence}


def evaluate(
    rows: dict[str, list[dict[str, Any]]],
    cable_count: int,
    cable_variant: str,
    route_length: str = "known",
) -> dict[str, Any]:
    choices = FIXTURE["fillDemo"]
    if type(cable_count) is not int or cable_count not in choices["cableCountChoices"]:
        raise ValueError("cableCount fuera del conjunto cerrado")
    if route_length not in choices["routeLengthChoices"]:
        raise ValueError("routeLength fuera del conjunto cerrado")
    legacy_mm = cable_variant if cable_variant in ("5", "6") else None
    if legacy_mm is not None:
        cable_od_in = str(Decimal(legacy_mm) / Decimal("25.4"))
        cable_source = "synthetic://guided-bom/legacy-mm-fixture"
    elif cable_variant in choices["cableVariants"]:
        cable_od_in = choices["cableVariants"][cable_variant]["nominalOuterDiameterIn"]
        cable_source = choices["cableVariants"][cable_variant]["source"]
    else:
        raise ValueError("cableVariant fuera del conjunto cerrado")
    route_rows = rows["route"]
    if len(route_rows) != 3 or {r["family"] for r in route_rows} != {
        "coupling",
        "connector",
        "support",
    }:
        raise ValueError("Relaciones del tramo incompletas")
    route_evidence = FIXTURE["route"]["evidenceId"]
    if any(row["evidenceId"] != route_evidence for row in route_rows):
        raise ValueError("Evidencia del tramo inconsistente")
    materials = [r for r in rows["materials"] if r["family"] == "emt"]
    accessories = [
        r for r in rows["accessories"] if r["family"] in {"coupling", "connector", "support"}
    ]
    if len(materials) != 3 or len(accessories) != 9:
        raise ValueError("Catálogo Relate incompleto")

    candidate_emt: list[dict[str, Any]] = []
    for row in materials:
        dimensions = choices["conduit"][row["diameter"]]
        inner_diameter = Decimal(dimensions["nominalOuterDiameterIn"]) - 2 * Decimal(
            dimensions["nominalWallThicknessIn"]
        )
        if str(inner_diameter) != dimensions["derivedInnerDiameterIn"]:
            raise ValueError("Diámetro interior derivado inconsistente")
        fill = _fill(cable_count, cable_od_in, str(inner_diameter))
        candidate_emt.append(
            {
                "itemId": row["itemId"],
                "family": "emt",
                "diameter": row["diameter"],
                "innerDiameterIn": str(inner_diameter),
                "status": "PENDING_CABLE_OD"
                if fill["eligible"] is None
                else "ELIGIBLE_FOR_DEMO"
                if fill["eligible"]
                else "REJECTED_BY_DEMO_FILL",
                "reasonCodes": ["CABLE_OD_UNKNOWN"]
                if fill["eligible"] is None
                else ["ILLUSTRATIVE_FILL_PASS"]
                if fill["eligible"]
                else ["ILLUSTRATIVE_FILL_EXCEEDED"],
                "fill": fill,
                "evidencePaths": _path(row, "MATERIAL"),
            }
        )
    candidate_emt.sort(key=lambda c: Decimal(c["innerDiameterIn"]))
    selected = next((c for c in candidate_emt if c["fill"]["eligible"]), None)
    if selected is None and cable_od_in is not None:
        raise ValueError("Ningún EMT del fixture satisface el criterio ilustrativo")
    diameter = selected["diameter"] if selected else None
    accessory_candidates: list[dict[str, Any]] = []
    selected_accessories: dict[str, str] = {}
    for row in accessories:
        eligible = diameter is not None and row["diameter"] == diameter
        if eligible:
            selected_accessories[row["family"]] = row["itemId"]
        accessory_candidates.append(
            {
                "itemId": row["itemId"],
                "family": row["family"],
                "diameter": row["diameter"],
                "status": "PENDING_CABLE_OD"
                if diameter is None
                else "ELIGIBLE_FOR_DEMO"
                if eligible
                else "DIAMETER_MISMATCH",
                "reasonCodes": ["CABLE_OD_UNKNOWN"]
                if diameter is None
                else ["SAME_DIAMETER"]
                if eligible
                else ["DIFFERENT_DIAMETER"],
                "evidencePaths": _path(row, "ACCESSORY"),
            }
        )
    if selected and set(selected_accessories) != {"coupling", "connector", "support"}:
        raise ValueError("Accesorios Relate incompletos para el diámetro")

    catalog = {"items": [*HARDWARE["catalog"]["items"]]}
    for row in [*materials, *accessories]:
        if row["diameter"] == "1 1/4":
            item = {
                "id": row["itemId"],
                "family": row["family"],
                "diameter": row["diameter"],
                "evidenceId": row["evidenceId"],
            }
            if row["family"] == "emt":
                item["commercialLengthM"] = "3"  # ficción coherente con AT-238
            catalog["items"].append(item)
    if selected and route_length == "known":
        route = {
            **FIXTURE["route"],
            "confirmed": True,
            "diameter": diameter,
            "selectedAccessories": selected_accessories,
        }
        derived = evaluate_route(catalog, route)
        if derived["status"] != "DERIVED":
            raise ValueError("AT-238 no pudo derivar el tramo")
    else:
        derived = evaluate_route(catalog, {"confirmed": False})

    scope = build_scope_draft(
        ScopeIntake(
            description="Tres cámaras Wi-Fi ficticias en sitio sin red ni internet",
            objective=ScopeFact("Observación local por tres cámaras", Certainty.INFERRED),
            location=ScopeFact("Sitio ficticio", Certainty.INFERRED),
            measurements=ScopeFact(
                (Measurement("tramo A", 2.0, "m"), Measurement("tramo B", 1.5, "m")),
                Certainty.CONFIRMED,
                route_evidence,
            )
            if route_length == "known"
            else None,
        )
    )
    mesh = next(p for p in PATTERNS if p["id"] == "at247:pattern:mesh")
    mesh_expansion = expand(
        mesh,
        {
            "application": _confirmed(True, "EV-GUIDED-OPTION"),
            "backhaul": _confirmed("wireless", "EV-GUIDED-OPTION"),
        },
    )
    topology = evaluate_topology(
        {"cables": [], "terminations": []},
        {
            "endpoints": [
                {"id": f"WIFI-CAM-{n}", "medium": "wifi_solar", "evidenceId": "EV-GUIDED-OPTION"}
                for n in range(1, 4)
            ],
            "ports": {},
            "uplinkRequired": False,
            "runs": [],
        },
    )
    if topology["links"]:
        raise ValueError("Las cámaras Wi-Fi ficticias no exigen enlaces Ethernet directos")
    route_paths = [
        {
            "nodes": [
                {"id": r["routeId"], "type": "INSTALLATION_SEGMENT"},
                {"id": r["requirementId"], "type": "REQUIREMENT"},
                {"id": r["evidenceId"], "type": "EVIDENCE"},
            ],
            "relations": ["REQUIRES", "SUPPORTED_BY"],
            "ruleId": r["ruleId"],
        }
        for r in route_rows
    ]
    return {
        "wireVersion": "guided-bom.v1",
        "scenarioId": FIXTURE["scenarioId"],
        "notice": FIXTURE["notice"],
        "assumptions": [
            {"id": "CAMERAS-WIFI", "value": 3, "state": "inferred"},
            {"id": "SATELLITE-CONNECTIVITY", "value": "optional", "state": "inferred"},
        ],
        "requirements": [
            {
                "id": "UTP-IN-ROUTE",
                "value": cable_count,
                "unit": "cables",
                "state": "confirmed",
                "evidenceId": route_evidence,
            },
            {
                "id": "CABLE-OD",
                "value": cable_od_in,
                "unit": "in",
                "state": "unknown" if cable_od_in is None else "confirmed",
                "evidenceId": cable_source,
                "variant": cable_variant,
            },
            {
                "id": "ROUTE-SECTIONS",
                "value": FIXTURE["route"]["sectionLengthsM"] if route_length == "known" else None,
                "unit": "m",
                "state": "confirmed" if route_length == "known" else "unknown",
                "evidenceId": route_evidence if route_length == "known" else None,
            },
        ],
        "bom": [
            {
                "itemId": line["material_id"],
                "family": line["family"],
                "quantity": line["quantity"],
                "unit": line["unit"],
                "state": "draft",
                "ruleId": line["rule_id"],
                "evidenceIds": line["evidence_ids"],
            }
            for line in derived["lines"]
        ],
        "candidates": {
            "emt": candidate_emt,
            "accessories": sorted(accessory_candidates, key=lambda c: c["itemId"]),
            "cameras": [
                {
                    "itemId": "WIFI-CAMERA-TYPE-UNSPECIFIED",
                    "quantity": 3,
                    "status": "NEEDS_POWER_AND_COVERAGE_VALIDATION",
                    "price": None,
                }
            ],
            "cables": [
                {
                    "itemId": "UTP-TYPE-UNSPECIFIED",
                    "quantityInRoute": cable_count,
                    "outerDiameterIn": cable_od_in,
                    "variant": cable_variant,
                    "status": "NEEDS_LINK_TOPOLOGY_AND_LENGTH",
                    "price": None,
                }
            ],
            "connectivity": [
                {
                    "itemId": "STARLINK-OPTION",
                    "label": "Starlink, opción conceptual sin verificar",
                    "status": "NEEDS_SITE_VALIDATION",
                    "price": None,
                    "sourceRef": "synthetic://guided-bom/connectivity-option",
                },
                {
                    "itemId": "LOCAL-WIFI-OPTION",
                    "status": "NEEDS_SITE_VALIDATION",
                    "patternCandidates": [c["itemId"] for c in mesh_expansion.candidates],
                    "pending": list(mesh_expansion.pending),
                },
            ],
            "switch": [],
            "enclosure": [],
        },
        "evidence": {
            "graphPaths": route_paths,
            "fillCriterion": {
                "fraction": choices["thresholdFraction"],
                "sourceRef": choices["thresholdSource"],
                "basis": "n*cable_od_in^2 <= fraction*conduit_inner_diameter_in^2",
                "comparison": "exact_decimal_before_display_rounding",
            },
            "primarySources": {
                "cable": cable_source,
                "conduit": choices["conduitSource"],
            },
            "at238ValidationTopics": derived["validationTopics"],
            "at239DirectCameraLinks": len(topology["links"]),
        },
        "status": {
            "code": "PENDING_REVIEW",
            "selectedDemoEmtId": selected["itemId"] if selected else None,
            "compatibility": "PENDING_OD" if selected is None else "ILLUSTRATIVE_CANDIDATE",
            "unknown": sorted(
                {q.field for q in scope.blocking_questions}
                | {
                    "wifi_coverage",
                    "camera_power",
                    "internet_service",
                    "power_source",
                    "physical_link_topology",
                    "local_code",
                    "real_dimensions",
                    "prices",
                    *(["cable_outer_diameter"] if cable_od_in is None else []),
                    *(["route_length", "bom_quantities"] if route_length == "unknown" else []),
                }
            ),
            "professionalValidationRequired": True,
        },
    }


class GuidedBomAgent(BaseAgent):
    """Agente ADK sin modelo: FunctionTool fijo y resultado determinista."""

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        tool = FunctionTool(graph_evidence)
        rows = await tool.run_async(
            args={"store_path": ctx.session.state["store_path"]},
            tool_context=ToolContext(ctx),
        )
        result = evaluate(
            rows,
            ctx.session.state["cable_count"],
            ctx.session.state["cable_variant"],
            ctx.session.state["route_length"],
        )
        yield Event(
            author=self.name,
            content=types.Content(
                role="model", parts=[types.Part.from_text(text=json.dumps(result, sort_keys=True))]
            ),
        )


async def run(
    store_path: Path, cable_count: int, cable_variant: str, route_length: str = "known"
) -> dict[str, Any]:
    runner = InMemoryRunner(agent=GuidedBomAgent(name="guided_bom"), app_name="guided_bom_demo")
    try:
        session = await runner.session_service.create_session(
            app_name="guided_bom_demo",
            user_id="synthetic_local",
            state={
                "store_path": str(store_path),
                "cable_count": cable_count,
                "cable_variant": cable_variant,
                "route_length": route_length,
            },
        )
        outputs: list[dict[str, Any]] = []
        async for event in runner.run_async(
            user_id="synthetic_local",
            session_id=session.id,
            new_message=types.Content(
                role="user", parts=[types.Part.from_text(text="guided fixture")]
            ),
        ):
            if event.is_final_response() and event.content and event.content.parts:
                outputs.append(cast(dict[str, Any], json.loads(event.content.parts[0].text or "")))
        if len(outputs) != 1:
            raise ValueError("ADK no produjo una salida única")
        return outputs[0]
    finally:
        await runner.close()  # type: ignore[no-untyped-call]  # ADK 1.20 no tipa close.


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BOM guiada ficticia; sin LLM ni proveedor")
    parser.add_argument("command", choices=["seed", "evaluate"])
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--cable-count", "--utp-count", type=int, choices=[3, 6])
    variants = parser.add_mutually_exclusive_group()
    variants.add_argument("--cable-variant", choices=["thick", "slim", "unknown"])
    variants.add_argument("--cable-od-mm", choices=["5", "6"])
    parser.add_argument("--route-length", choices=["known", "unknown"], default="known")
    args = parser.parse_args(argv)
    try:
        if args.command == "seed":
            if (
                args.cable_count is not None
                or args.cable_variant is not None
                or args.cable_od_mm is not None
                or args.route_length != "known"
            ):
                raise ValueError("seed no acepta requisitos")
            seed(args.store)
            result: dict[str, Any] = {"scenarioId": FIXTURE["scenarioId"], "seeded": True}
        else:
            variant = args.cable_variant or args.cable_od_mm
            if args.cable_count is None or variant is None:
                raise ValueError("evaluate requiere cable-count y cable-variant")
            result = asyncio.run(run(args.store, args.cable_count, variant, args.route_length))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, relate.RelateError) as error:
        parser.exit(2, f"error: {error}\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
