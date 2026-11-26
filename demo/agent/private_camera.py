"""Entrada privada sintética de cámaras: ADK → OpenAI → Relate fijo."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any, Protocol, cast

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.runners import InMemoryRunner
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types
from pydantic import Field

from demo.agent.agent import EvaluationRequest, _camera_result
from demo.agent.graph import camera_stock_evidence
from demo.private_counts import COUNT_SERIES, has_qualifier, parse_series
from demo.private_model import DEFAULT_MODEL, MAX_DESCRIPTION_CHARS, OpenAIJsonExtractor

PROMPT = (
    "Extrae solo la cantidad inequívoca de cámaras solicitadas de este texto ficticio en español. "
    "Devuelve 2, 4 o null. Si falta, hay alternativas, contradicción o ambigüedad, devuelve null. "
    "No derives inventario, compatibilidad, precios ni evidencia: eso lo decide el grafo local."
)
SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"requested_quantity": {"type": ["integer", "null"], "enum": [2, 4, None]}},
    "required": ["requested_quantity"],
    "additionalProperties": False,
}
QUESTION = "¿Cuántas cámaras se solicitan: dos o cuatro?"
CAMERA_NOUN = r"(?:c[aá]maras?|cameras?)"
CAMERA_COUNT = re.compile(
    rf"(?<![\w.,+-])(?:(?P<before>{COUNT_SERIES})\s+{CAMERA_NOUN}\b"
    rf"|{CAMERA_NOUN}\s+(?P<after>{COUNT_SERIES})(?![\w.,]))"
)


class CameraExtractor(Protocol):
    async def extract(self, description: str) -> tuple[dict[str, Any], dict[str, int] | None]: ...


class OpenAICameraExtractor(OpenAIJsonExtractor):
    def __init__(self, model: str = DEFAULT_MODEL):
        super().__init__(prompt=PROMPT, schema=SCHEMA, name="camera_scope", model=model)


def _validated_quantity(description: str, raw: dict[str, Any]) -> int | None:
    if not isinstance(raw, dict) or set(raw) != {"requested_quantity"}:
        raise ValueError("Extracción de cámara fuera de esquema")
    quantity = raw["requested_quantity"]
    if type(quantity) not in (int, type(None)) or quantity not in (2, 4, None):
        raise ValueError("Cantidad no permitida")
    normalized = description.casefold().replace(",", ".")
    matches = []
    for match in CAMERA_COUNT.finditer(normalized):
        if has_qualifier(normalized, match.start()):
            if quantity is not None:
                raise ValueError("Cantidad sin respaldo inequívoco")
            return None
        matches.extend(parse_series(match.group("before") or match.group("after")))
    if quantity is not None and matches != [quantity]:
        raise ValueError("Cantidad sin respaldo inequívoco")
    # Un null ante texto inequívoco es conservador: pide confirmación al usuario.
    return cast(int | None, quantity)


class PrivateCameraAgent(BaseAgent):
    extractor: Any = Field(exclude=True)

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        description = ctx.session.state["description"]
        raw, metrics = await self.extractor.extract(description)
        quantity = _validated_quantity(description, raw)
        evaluation = None
        evidence_ids: list[str] = []
        tool_calls = 0
        if quantity is not None:
            rows = await FunctionTool(camera_stock_evidence).run_async(
                args={"store_path": ctx.session.state["store_path"], "quantity": quantity},
                tool_context=ToolContext(ctx),
            )
            if not isinstance(rows, list):
                raise ValueError("Relate no devolvió filas válidas")
            evaluation = _camera_result(rows, EvaluationRequest("camera", quantity=quantity))
            evidence_ids = sorted(
                {
                    node["id"]
                    for candidate in evaluation["candidates"]
                    for path in candidate["evidencePaths"]
                    for node in path["nodes"]
                    if node["type"] == "EVIDENCE"
                }
            )
            if not {"EV-CAM-POE", "EV-POOL-CAM"}.issubset(evidence_ids):
                raise ValueError("Faltó evidencia técnica o del pool compartido")
            tool_calls = 1
        result = {
            "mode": "private-camera-intake.v1",
            "status": "NEEDS_QUANTITY" if quantity is None else "PENDING_REVIEW",
            "requestedQuantity": quantity,
            "question": QUESTION if quantity is None else None,
            "evaluation": evaluation,
            "evidenceIds": evidence_ids,
            "toolCalls": tool_calls,
            "model": getattr(self.extractor, "model", DEFAULT_MODEL),
            "usage": metrics,
        }
        yield Event(
            author=self.name,
            content=types.Content(
                role="model", parts=[types.Part.from_text(text=json.dumps(result, sort_keys=True))]
            ),
        )


async def run_camera(
    store_path: Path, description: str, extractor: CameraExtractor
) -> dict[str, Any]:
    if not 1 <= len(description) <= MAX_DESCRIPTION_CHARS:
        raise ValueError("Descripción fuera del límite de 700 caracteres")
    runner = InMemoryRunner(
        agent=PrivateCameraAgent(name="private_camera", extractor=extractor),
        app_name="private_camera_demo",
    )
    try:
        session = await runner.session_service.create_session(
            app_name="private_camera_demo",
            user_id="private_synthetic",
            state={"store_path": str(store_path), "description": description},
        )
        outputs: list[dict[str, Any]] = []
        async for event in runner.run_async(
            user_id="private_synthetic",
            session_id=session.id,
            new_message=types.Content(role="user", parts=[types.Part.from_text(text="extract")]),
        ):
            if event.is_final_response() and event.content and event.content.parts:
                outputs.append(cast(dict[str, Any], json.loads(event.content.parts[0].text or "")))
        if len(outputs) != 1:
            raise ValueError("ADK no produjo una salida única")
        return outputs[0]
    finally:
        await runner.close()  # type: ignore[no-untyped-call]  # ADK 1.20 no tipa close.


def main() -> int:
    parser = argparse.ArgumentParser(description="Entrada de cámaras privada; fixture ficticia")
    parser.add_argument("--store", required=True, type=Path)
    parser.add_argument("--description", required=True)
    parser.add_argument(
        "--model", default=DEFAULT_MODEL, help="Modelo explícito; gpt-6-luna por defecto"
    )
    args = parser.parse_args()
    try:
        output = asyncio.run(
            run_camera(args.store, args.description, OpenAICameraExtractor(args.model))
        )
        print(json.dumps(output, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception:
        # No exponer cuerpos, excepciones del proveedor ni contenido de la entrada.
        parser.exit(2, "error: extracción privada falló; revisar configuración y fixture\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
