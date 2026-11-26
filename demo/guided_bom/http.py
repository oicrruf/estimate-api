"""GET local, sintético y de sólo lectura para la vista guiada."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Annotated, Any, Literal

import relate
import uvicorn
from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict

from demo.guided_bom.cli import FIXTURE, graph_evidence, run


class GuidedResponse(BaseModel):
    """Sobre versionado; el ejemplo JSON congela el detalle anidado del demo."""

    model_config = ConfigDict(extra="forbid")

    wireVersion: Literal["guided-bom.v1"]
    scenarioId: Literal["synthetic-three-wifi-cameras-no-network"]
    notice: str
    assumptions: list[dict[str, Any]]
    requirements: list[dict[str, Any]]
    bom: list[dict[str, Any]]
    candidates: dict[str, Any]
    evidence: dict[str, Any]
    status: dict[str, Any]


def create_app(store: Path) -> FastAPI:
    """El store se fija al iniciar; ninguna URL de petición cambia ruta o grafo."""
    resolved = store.resolve()
    rows = graph_evidence(str(resolved))
    if len(rows["route"]) != 3 or len(rows["materials"]) != 3 or len(rows["accessories"]) < 9:
        raise ValueError("Fixture guiada incompleta")
    app = FastAPI(title="Synthetic guided BOM preview", version="guided-bom.v1", redoc_url=None)

    @app.get("/v1/demo/guided-bom", response_model=GuidedResponse, operation_id="guidedBomV1")
    async def guided_bom(
        request: Request,
        cable_count: Annotated[int, Query(ge=3, le=6)],
        cable_variant: Literal["thick", "slim", "unknown"],
        route_length: Literal["known", "unknown"] = "known",
    ) -> GuidedResponse:
        keys = [key for key, _ in request.query_params.multi_items()]
        if len(keys) != len(set(keys)) or set(keys) - {
            "cable_count",
            "cable_variant",
            "route_length",
        }:
            raise HTTPException(status_code=422, detail="Parámetros duplicados o desconocidos")
        if cable_count not in (3, 6):
            raise HTTPException(status_code=422, detail="cable_count sólo acepta 3 o 6")
        try:
            result = await run(resolved, cable_count, cable_variant, route_length)
            if result["scenarioId"] != FIXTURE["scenarioId"]:
                raise ValueError("Escenario inesperado")
            return GuidedResponse.model_validate(result)
        except (ValueError, relate.RelateError) as error:
            raise HTTPException(status_code=503, detail="Fixture guiada no disponible") from error

    return app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GET sintético local ADK/Relate")
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8002)
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("--port debe estar entre 1 y 65535")
    try:
        app = create_app(args.store)
    except (ValueError, relate.RelateError) as error:
        parser.exit(2, f"error: {error}\n")
    uvicorn.run(app, host="127.0.0.1", port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
