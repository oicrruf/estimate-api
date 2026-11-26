"""Corte privado: extracción OpenAI acotada, agente ADK y evidencia Relate local."""

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

from demo.guided_bom.cli import evaluate, graph_evidence
from demo.private_model import DEFAULT_MODEL, MAX_DESCRIPTION_CHARS, OpenAIJsonExtractor

MODEL = DEFAULT_MODEL
PROMPT = (
    "Extrae solamente datos explícitos de esta descripción ficticia en español. "
    "cable_count es la cantidad de UTP en el tramo, no la cantidad de cámaras. "
    "cable_variant es thick solo si consta OD 0.278 in o 10GXS32; slim solo si "
    "consta OD 0.224 in o 2412; de otro modo unknown. "
    "route_length es known solo si constan tramos de 2 m y 1.5 m; de otro modo unknown. "
    "Nunca inventes cantidades, precios, compatibilidades, mediciones ni evidencia. "
    "Devuelve preguntas faltantes como IDs cable_count, cable_od o route_length."
)
SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "cable_count": {"type": ["integer", "null"], "enum": [3, 6, None]},
        "cable_variant": {"type": "string", "enum": ["thick", "slim", "unknown"]},
        "route_length": {"type": "string", "enum": ["known", "unknown"]},
        "missing": {
            "type": "array",
            "items": {"type": "string", "enum": ["cable_count", "cable_od", "route_length"]},
        },
    },
    "required": ["cable_count", "cable_variant", "route_length", "missing"],
    "additionalProperties": False,
}
QUESTIONS = {
    "cable_count": "¿Cuántos cables UTP irán en el tramo?",
    "cable_od": "¿Cuál es el diámetro exterior nominal del cable elegido?",
    "route_length": "¿Cuáles son las longitudes medidas de los tramos?",
}


class ScopeExtractor(Protocol):
    async def extract(self, description: str) -> tuple[dict[str, Any], dict[str, int] | None]: ...


class OpenAIScopeExtractor(OpenAIJsonExtractor):
    def __init__(self, model: str = MODEL):
        super().__init__(prompt=PROMPT, schema=SCHEMA, name="guided_scope", model=model)


def _validated_scope(description: str, raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict) or set(raw) != set(SCHEMA["required"]):
        raise ValueError("Extracción fuera de esquema")
    count = raw["cable_count"]
    variant = raw["cable_variant"]
    length = raw["route_length"]
    missing = raw["missing"]
    if type(count) not in (int, type(None)) or count not in (3, 6, None):
        raise ValueError("Cantidad no permitida")
    if variant not in ("thick", "slim", "unknown") or length not in ("known", "unknown"):
        raise ValueError("Selección no permitida")
    if not isinstance(missing, list) or not all(x in QUESTIONS for x in missing):
        raise ValueError("Preguntas no permitidas")
    normalized = description.lower().replace(",", ".")
    if count is not None:
        number = "tres" if count == 3 else "seis"
        pattern = (
            rf"(?:\b(?:{count}|{number})\s+(?:cables?\s+)?utp\b|"
            rf"\butp\s+(?:{count}|{number})\b)"
        )
        if not re.search(pattern, normalized):
            raise ValueError("Cantidad UTP sin respaldo literal")
    if variant == "thick" and not re.search(r"0\.278|10gxs32", normalized):
        raise ValueError("OD grueso sin respaldo literal")
    if variant == "slim" and not re.search(r"0\.224|2412", normalized):
        raise ValueError("OD delgado sin respaldo literal")
    if length == "known" and not ("2 m" in normalized and "1.5 m" in normalized):
        raise ValueError("Longitud sin respaldo literal")
    required = set()
    if count is None:
        required.add("cable_count")
    if variant == "unknown":
        required.add("cable_od")
    if length == "unknown":
        required.add("route_length")
    return {
        "cableCount": count,
        "cableVariant": variant,
        "routeLength": length,
        "questions": [QUESTIONS[key] for key in sorted(required)],
        "states": {
            "cableCount": "unknown" if count is None else "inferred",
            "cableVariant": "unknown" if variant == "unknown" else "inferred",
            "routeLength": "unknown" if length == "unknown" else "inferred",
        },
    }


class PrivateGuidedAgent(BaseAgent):
    extractor: Any = Field(exclude=True)

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        description = ctx.session.state["description"]
        raw, usage = await self.extractor.extract(description)
        scope = _validated_scope(description, raw)
        rows = await FunctionTool(graph_evidence).run_async(
            args={"store_path": ctx.session.state["store_path"]},
            tool_context=ToolContext(ctx),
        )
        evidence_ids = sorted({row["evidenceId"] for group in rows.values() for row in group})
        if not evidence_ids or len(rows["route"]) != 3:
            raise ValueError("Relate no devolvió evidencia completa")
        preview = None
        if scope["cableCount"] is not None:
            preview = evaluate(
                rows, scope["cableCount"], scope["cableVariant"], scope["routeLength"]
            )
        result = {
            "scenarioId": "guided-bom-private-ai.v1",
            "status": "PENDING_REVIEW",
            "scope": scope,
            "evidenceIds": evidence_ids,
            "preview": preview,
            "model": getattr(self.extractor, "model", MODEL),
            "usage": usage,
        }
        yield Event(
            author=self.name,
            content=types.Content(
                role="model", parts=[types.Part.from_text(text=json.dumps(result, sort_keys=True))]
            ),
        )


async def run_private(
    store_path: Path, description: str, extractor: ScopeExtractor
) -> dict[str, Any]:
    if not 1 <= len(description) <= MAX_DESCRIPTION_CHARS:
        raise ValueError("Descripción fuera del límite de 700 caracteres")
    if not store_path.is_file():
        raise ValueError("Store sintético requerido")
    runner = InMemoryRunner(
        agent=PrivateGuidedAgent(name="private_guided", extractor=extractor),
        app_name="private_guided_demo",
    )
    try:
        session = await runner.session_service.create_session(
            app_name="private_guided_demo",
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
    parser = argparse.ArgumentParser(description="ADK/OpenAI/Relate privado; fixture ficticia")
    parser.add_argument("--store", required=True, type=Path)
    parser.add_argument("--description", required=True)
    parser.add_argument(
        "--model", default=MODEL, help="Modelo explícito; predeterminado gpt-6-luna"
    )
    args = parser.parse_args()
    try:
        result = asyncio.run(
            run_private(args.store, args.description, OpenAIScopeExtractor(args.model))
        )
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception:
        # El SDK puede incluir detalles de petición en excepciones; salida deliberadamente saneada.
        parser.exit(2, "error: extracción privada falló; revisar configuración y fixture\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
