"""Transporte Responses privado y acotado para los agentes locales de demo."""

from __future__ import annotations

import json
import os
import re
from typing import Any, cast

DEFAULT_MODEL = "gpt-6-luna"
MAX_DESCRIPTION_CHARS = 700
MAX_OUTPUT_TOKENS = 500
MAX_INPUT_TOKENS = 4000


def configured_model(value: str = DEFAULT_MODEL) -> str:
    """Selección explícita; un modelo alterno jamás se elige por error/reintento."""
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", value):
        raise ValueError("ID de modelo inválido")
    return value


class OpenAIJsonExtractor:
    def __init__(
        self, *, prompt: str, schema: dict[str, Any], name: str, model: str = DEFAULT_MODEL
    ):
        self.prompt = prompt
        self.schema = schema
        self.name = name
        self.model = configured_model(model)

    async def extract(self, description: str) -> tuple[dict[str, Any], dict[str, int]]:
        if not 1 <= len(description) <= MAX_DESCRIPTION_CHARS:
            raise ValueError("Descripción fuera del límite de 700 caracteres")
        if not os.environ.get("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY ausente en este proceso")
        from openai import AsyncOpenAI  # dependencia opcional del modo privado

        client = AsyncOpenAI(timeout=15.0, max_retries=0)
        try:
            raw = await client.responses.with_raw_response.create(
                model=self.model,
                reasoning={"effort": "none"},
                instructions=self.prompt,
                input=description,
                max_output_tokens=MAX_OUTPUT_TOKENS,
                tools=[],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": self.name,
                        "strict": True,
                        "schema": self.schema,
                    }
                },
                store=False,
            )
            # El SDK devuelve un objeto tipado. No leer ni registrar cuerpo crudo.
            if raw.status_code != 200:
                raise ValueError("Respuesta HTTP no satisfactoria")
            response = raw.parse()
            if response.status != "completed" or not response.output_text:
                raise ValueError("OpenAI no produjo una extracción completa")
            usage = response.usage
            metrics = {"httpStatus": raw.status_code}
            if usage is not None:
                if usage.input_tokens > MAX_INPUT_TOKENS or usage.output_tokens > MAX_OUTPUT_TOKENS:
                    raise ValueError("Presupuesto de tokens excedido")
                metrics.update(
                    {"inputTokens": usage.input_tokens, "outputTokens": usage.output_tokens}
                )
            output = json.loads(response.output_text)
            if not isinstance(output, dict):
                raise ValueError("Extracción no estructurada")
            return cast(dict[str, Any], output), metrics
        finally:
            await client.close()
