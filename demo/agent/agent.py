"""Agente ADK local: herramientas Relate fijas y decisiones deterministas."""

import json
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any, Literal, cast

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.runners import InMemoryRunner
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types

from demo.agent.graph import camera_stock_evidence, switch_evidence, ups_evidence

Scenario = Literal["switch", "camera", "ups"]


@dataclass(frozen=True)
class EvaluationRequest:
    scenario: Scenario
    poe_ports_min: int = 8
    quantity: int = 4

    def __post_init__(self) -> None:
        if self.scenario not in ("switch", "camera", "ups"):
            raise ValueError("Escenario desconocido")
        if type(self.poe_ports_min) is not int or not 1 <= self.poe_ports_min <= 16:
            raise ValueError("poe_ports_min debe ser un entero entre 1 y 16")
        if type(self.quantity) is not int or not 1 <= self.quantity <= 16:
            raise ValueError("quantity debe ser un entero entre 1 y 16")


def _paths(row: dict[str, Any]) -> list[dict[str, Any]]:
    paths: list[dict[str, Any]] = row["evidencePaths"]
    for path in paths:
        if len(path["nodes"]) != len(path["relations"]) + 1:
            raise ValueError("Ruta de evidencia inválida")
        if not any(node["type"] == "EVIDENCE" for node in path["nodes"]):
            # Las aristas del requisito son parciales; la capacidad técnica tiene evidencia.
            if path["nodes"][0]["type"] != "REQUIREMENT":
                raise ValueError("Capacidad técnica sin evidencia")
    return paths


def _switch_result(rows: list[dict[str, Any]], request: EvaluationRequest) -> dict[str, Any]:
    if len(rows) != 2:
        raise ValueError("Fixture de switches incompleto")
    candidates = []
    for row in rows:
        required_total = request.poe_ports_min + row["distinctUplinkPorts"]
        reasons = []
        if row["totalPorts"] < required_total:
            reasons.append("TOTAL_PORTS_BELOW_REQUIRED")
        if row["poePorts"] < request.poe_ports_min:
            reasons.append("POE_PORTS_BELOW_REQUIRED")
        if row["poeBudgetW"] < row["requiredPoeBudgetW"]:
            reasons.append("POE_BUDGET_BELOW_REQUIRED")
        if reasons:
            status = "INCOMPATIBLE"
        elif row["offerQuantity"] < 1:
            reasons.append("INSUFFICIENT_STOCK")
            status = "INSUFFICIENT_STOCK"
        else:
            status = "COMPATIBLE"
        candidates.append(
            {
                "productId": row["productId"],
                "offerIds": [row["offerId"]],
                "fictitiousPriceUsd": row["fictitiousPriceUsd"],
                "status": status,
                "reasonCodes": reasons or ["MEETS_REQUIREMENTS"],
                "measured": {
                    "totalPorts": row["totalPorts"],
                    "poePorts": row["poePorts"],
                    "poeBudgetW": row["poeBudgetW"],
                },
                "evidencePaths": _paths(row),
            }
        )
    candidates.sort(
        key=lambda item: (
            item["status"] != "COMPATIBLE",
            item["fictitiousPriceUsd"],
            item["productId"],
        )
    )
    selected = next(
        (item["productId"] for item in candidates if item["status"] == "COMPATIBLE"), None
    )
    return {
        "scenario": "switch",
        "requirementId": "REQ-SWITCH",
        "requested": {
            "poePortsMin": request.poe_ports_min,
            "distinctUplinkPorts": rows[0]["distinctUplinkPorts"],
            "totalPortsMin": request.poe_ports_min + rows[0]["distinctUplinkPorts"],
            "poeBudgetWMin": rows[0]["requiredPoeBudgetW"],
        },
        "selectedProductId": selected,
        "candidates": candidates,
    }


def _camera_result(rows: list[dict[str, Any]], request: EvaluationRequest) -> dict[str, Any]:
    if len(rows) != 1:
        raise ValueError("Fixture de cámara incompleto")
    row = rows[0]
    available = min(row["listedQuantity"], row["poolCapacity"])
    reasons = []
    if row["resolutionMp"] < row["requiredResolutionMp"] or row["power"] != "PoE":
        reasons.append("TECHNICAL_REQUIREMENT_NOT_MET")
    if available < request.quantity:
        reasons.append("SHARED_POOL_CAPACITY")
    status = (
        "INCOMPATIBLE"
        if "TECHNICAL_REQUIREMENT_NOT_MET" in reasons
        else ("INSUFFICIENT_STOCK" if reasons else "COMPATIBLE")
    )
    return {
        "scenario": "camera",
        "requirementId": row["requirementId"],
        "requestedQuantity": request.quantity,
        "availableQuantity": available,
        "selectedProductId": row["productId"] if status == "COMPATIBLE" else None,
        "candidates": [
            {
                "productId": row["productId"],
                "offerIds": sorted(row["offerIds"]),
                "status": status,
                "reasonCodes": reasons or ["MEETS_REQUIREMENTS"],
                "measured": {
                    "resolutionMp": row["resolutionMp"],
                    "power": row["power"],
                    "poolCapacity": row["poolCapacity"],
                    "listedQuantity": row["listedQuantity"],
                },
                "evidencePaths": _paths(row),
            }
        ],
    }


def _ups_result(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if len(rows) != 1:
        raise ValueError("Fixture UPS incompleto")
    row = rows[0]
    compatible = row["capacityVa"] >= row["requiredCapacityVa"]
    return {
        "scenario": "ups",
        "requirementId": row["requirementId"],
        "selectedProductId": None,
        "candidates": [
            {
                "productId": row["productId"],
                "offerIds": [],
                "status": "TECHNICALLY_COMPATIBLE_NO_OFFER" if compatible else "INCOMPATIBLE",
                "reasonCodes": ["MEETS_TECHNICAL_REQUIREMENT_NO_OFFER"]
                if compatible
                else ["CAPACITY_BELOW_REQUIRED"],
                "measured": {
                    "capacityVa": row["capacityVa"],
                    "requiredCapacityVa": row["requiredCapacityVa"],
                },
                "evidencePaths": _paths(row),
            }
        ],
    }


class EvidenceAgent(BaseAgent):
    """Custom ADK agent sin LLM; sólo invoca FunctionTool de lectura."""

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        request = EvaluationRequest(**ctx.session.state["request"])
        store_path: str = ctx.session.state["store_path"]
        if request.scenario == "switch":
            tool = FunctionTool(switch_evidence)
            args = {"store_path": store_path, "poe_ports_min": request.poe_ports_min}
        elif request.scenario == "camera":
            tool = FunctionTool(camera_stock_evidence)
            args = {"store_path": store_path, "quantity": request.quantity}
        else:
            tool = FunctionTool(ups_evidence)
            args = {"store_path": store_path}
        rows = await tool.run_async(args=args, tool_context=ToolContext(ctx))
        if not isinstance(rows, list):
            raise ValueError("La herramienta no devolvió filas de Relate")
        if request.scenario == "switch":
            result = _switch_result(rows, request)
        elif request.scenario == "camera":
            result = _camera_result(rows, request)
        else:
            result = _ups_result(rows)
        result["engine"] = "google-adk-custom-agent-offline"
        result["tool"] = tool.name
        response_text = json.dumps(result, ensure_ascii=False, sort_keys=True)
        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text=response_text)],
            ),
        )


async def evaluate_offline(store_path: str, request: EvaluationRequest) -> dict[str, Any]:
    """Ejecutar el agente con ADK InMemoryRunner, sin instanciar modelo."""
    runner = InMemoryRunner(agent=EvidenceAgent(name="evidence_demo"), app_name="at227_demo")
    try:
        session = await runner.session_service.create_session(
            app_name="at227_demo",
            user_id="local_demo",
            state={
                "store_path": store_path,
                "request": {
                    "scenario": request.scenario,
                    "poe_ports_min": request.poe_ports_min,
                    "quantity": request.quantity,
                },
            },
        )
        results: list[dict[str, Any]] = []
        async for event in runner.run_async(
            user_id="local_demo",
            session_id=session.id,
            new_message=types.Content(
                role="user", parts=[types.Part.from_text(text="Evaluar fixture local")]
            ),
        ):
            if event.is_final_response() and event.content and event.content.parts:
                response_text = event.content.parts[0].text
                if response_text is None:
                    raise ValueError("ADK produjo una respuesta sin texto")
                results.append(cast(dict[str, Any], json.loads(response_text)))
        if len(results) != 1:
            raise ValueError("ADK no produjo una respuesta final única")
        return results[0]
    finally:
        await runner.close()
