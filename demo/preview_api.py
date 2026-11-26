"""Servidor HTTP local para la fixture AT-227; no forma parte de la API productiva."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Annotated, Literal

import relate
import uvicorn
from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from demo.agent.agent import EvaluationRequest, evaluate_offline
from demo.agent.graph import DATASET_ID


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidenceNode(StrictModel):
    id: str
    type: Literal["REQUIREMENT", "PRODUCT", "CAPABILITY", "EVIDENCE"]
    source: str | None = None


class EvidencePath(StrictModel):
    nodes: list[EvidenceNode]
    relations: list[Literal["REQUIRES", "SUPPORTS", "SUPPORTED_BY"]]


class CandidateBase(StrictModel):
    productId: str
    offerIds: list[str]
    status: Literal[
        "COMPATIBLE", "INCOMPATIBLE", "INSUFFICIENT_STOCK", "TECHNICALLY_COMPATIBLE_NO_OFFER"
    ]
    reasonCodes: list[str]
    evidencePaths: list[EvidencePath]


class SwitchMeasured(StrictModel):
    totalPorts: int
    poePorts: int
    poeBudgetW: int


class CameraMeasured(StrictModel):
    resolutionMp: int
    power: str
    poolCapacity: int
    listedQuantity: int


class UpsMeasured(StrictModel):
    capacityVa: int
    requiredCapacityVa: int


class SwitchCandidate(CandidateBase):
    fictitiousPriceUsd: int | float
    measured: SwitchMeasured


class CameraCandidate(CandidateBase):
    measured: CameraMeasured


class UpsCandidate(CandidateBase):
    measured: UpsMeasured


class SwitchRequested(StrictModel):
    poePortsMin: int
    distinctUplinkPorts: int
    totalPortsMin: int
    poeBudgetWMin: int


class ResultBase(StrictModel):
    requirementId: str
    selectedProductId: str | None
    engine: Literal["google-adk-custom-agent-offline"]


class SwitchResult(ResultBase):
    scenario: Literal["switch"]
    tool: Literal["switch_evidence"]
    requested: SwitchRequested
    candidates: list[SwitchCandidate]


class CameraResult(ResultBase):
    scenario: Literal["camera"]
    tool: Literal["camera_stock_evidence"]
    requestedQuantity: int
    availableQuantity: int
    candidates: list[CameraCandidate]


class UpsResult(ResultBase):
    scenario: Literal["ups"]
    tool: Literal["ups_evidence"]
    candidates: list[UpsCandidate]


EvaluationResult = Annotated[
    SwitchResult | CameraResult | UpsResult, Field(discriminator="scenario")
]
RESULT_ADAPTER: TypeAdapter[EvaluationResult] = TypeAdapter(EvaluationResult)


def _validate_store(path: Path) -> None:
    if not path.is_file():
        raise ValueError("La fixture Relate no existe; ejecute seed primero")
    connection = relate.connect(str(path), read_only=True)
    try:
        markers = connection.execute(
            "MATCH (e:EVIDENCE {datasetId:$dataset}) RETURN count(e) AS n",
            {"dataset": DATASET_ID},
        ).single()["n"]
        nodes = connection.execute("MATCH (n) RETURN count(n) AS n").single()["n"]
        relations = connection.execute("MATCH ()-[r]->() RETURN count(r) AS n").single()["n"]
        if markers == 0 or (nodes, relations) != (60, 61):
            raise ValueError("El store no contiene la fixture AT-229")
    finally:
        connection.close()


def create_app(store: Path) -> FastAPI:
    """Fijar la ruta del grafo al crear la app; ninguna petición puede cambiarla."""
    resolved = store.resolve()
    _validate_store(resolved)
    app = FastAPI(title="Estimate local preview", version="1.0.0", redoc_url=None)

    @app.get(
        "/v1/demo/evaluate",
        response_model=EvaluationResult,
        response_model_exclude_unset=True,
        operation_id="evaluateDemoV1",
    )
    async def evaluate_demo(
        request: Request,
        scenario: Literal["switch", "camera", "ups"],
        poe_ports_min: Annotated[int | None, Query(ge=1, le=16)] = None,
        quantity: Annotated[int | None, Query(ge=1, le=16)] = None,
    ) -> EvaluationResult:
        keys = [key for key, _ in request.query_params.multi_items()]
        if len(keys) != len(set(keys)) or set(keys) - {"scenario", "poe_ports_min", "quantity"}:
            raise HTTPException(status_code=422, detail="Parámetros duplicados o desconocidos")
        if scenario != "switch" and poe_ports_min is not None:
            raise HTTPException(status_code=422, detail="poe_ports_min sólo aplica a switch")
        if scenario != "camera" and quantity is not None:
            raise HTTPException(status_code=422, detail="quantity sólo aplica a camera")
        try:
            result = await evaluate_offline(
                str(resolved),
                EvaluationRequest(
                    scenario=scenario,
                    poe_ports_min=poe_ports_min if poe_ports_min is not None else 8,
                    quantity=quantity if quantity is not None else 4,
                ),
            )
            return RESULT_ADAPTER.validate_python(result)
        except (ValueError, relate.RelateError) as error:
            raise HTTPException(status_code=503, detail="Fixture local no disponible") from error

    return app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="HTTP local ADK/Relate; sólo loopback y fixture")
    parser.add_argument("--store", type=Path, required=True, help="Archivo .rl ya sembrado")
    parser.add_argument("--port", type=int, default=8001, help="Puerto loopback (1..65535)")
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
