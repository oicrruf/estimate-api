"""Consultas Relate fijas, de sólo lectura, sobre el fixture público AT-229."""

from pathlib import Path
from typing import Any

import relate

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
DATASET_ID = "estimate-hackathon-v1"

SWITCH_QUERY = """
MATCH (r:REQUIREMENT {id:'REQ-SWITCH'})-[:REQUIRES]->(reqPoe:CAPABILITY {key:'poePortsMin'})
MATCH (r)-[:REQUIRES]->(reqUplink:CAPABILITY {key:'distinctUplinkPorts'})
MATCH (r)-[:REQUIRES]->(reqBudget:CAPABILITY {key:'poeBudgetWMin'})
MATCH (o:OFFER)-[:SELLS]->(p:PRODUCT {kind:'switch'})
MATCH (p)-[:SUPPORTS]->(total:CAPABILITY {key:'totalPorts'})-[:SUPPORTED_BY]->(evTotal:EVIDENCE)
MATCH (p)-[:SUPPORTS]->(poe:CAPABILITY {key:'poePorts'})-[:SUPPORTED_BY]->(evPoe:EVIDENCE)
MATCH (p)-[:SUPPORTS]->(budget:CAPABILITY {key:'poeBudgetW'})-[:SUPPORTED_BY]->(evBudget:EVIDENCE)
RETURN r.id AS requirementId, p.id AS productId, o.id AS offerId,
  o.priceUsd AS fictitiousPriceUsd, o.quantity AS offerQuantity,
  total.value AS totalPorts, poe.value AS poePorts, budget.value AS poeBudgetW,
  reqUplink.value AS distinctUplinkPorts, reqBudget.value AS requiredPoeBudgetW,
  $poe_ports_min AS requiredPoePorts,
  [{nodes:[{id:r.id,type:'REQUIREMENT'},{id:reqPoe.id,type:'CAPABILITY'}],
    relations:['REQUIRES']},
   {nodes:[{id:r.id,type:'REQUIREMENT'},{id:reqUplink.id,type:'CAPABILITY'}],
    relations:['REQUIRES']},
   {nodes:[{id:p.id,type:'PRODUCT'},{id:total.id,type:'CAPABILITY'},
           {id:evTotal.id,type:'EVIDENCE',source:evTotal.source}],
    relations:['SUPPORTS','SUPPORTED_BY']},
   {nodes:[{id:p.id,type:'PRODUCT'},{id:poe.id,type:'CAPABILITY'},
           {id:evPoe.id,type:'EVIDENCE',source:evPoe.source}],
    relations:['SUPPORTS','SUPPORTED_BY']},
   {nodes:[{id:p.id,type:'PRODUCT'},{id:budget.id,type:'CAPABILITY'},
           {id:evBudget.id,type:'EVIDENCE',source:evBudget.source}],
    relations:['SUPPORTS','SUPPORTED_BY']}] AS evidencePaths
ORDER BY o.priceUsd, p.id
"""

CAMERA_QUERY = """
MATCH (r:REQUIREMENT {id:'REQ-CAMERA'})
MATCH (r)-[:REQUIRES]->(reqResolution:CAPABILITY {key:'resolutionMpMin'})
MATCH (o:OFFER)-[:SELLS]->(p:PRODUCT {id:'CAM-POE'})
MATCH (p)-[:SUPPORTS]->(pool:CAPABILITY {key:'poolCapacity'})-[:SUPPORTED_BY]->(evPool:EVIDENCE)
MATCH (p)-[:SUPPORTS]->(resolution:CAPABILITY {key:'resolutionMp'})
      -[:SUPPORTED_BY]->(evResolution:EVIDENCE)
MATCH (p)-[:SUPPORTS]->(power:CAPABILITY {key:'power'})-[:SUPPORTED_BY]->(evPower:EVIDENCE)
WITH r,p,pool,evPool,reqResolution,resolution,evResolution,power,evPower,
     collect(o.id) AS offerIds, sum(o.quantity) AS listedQuantity
RETURN r.id AS requirementId, p.id AS productId, offerIds, listedQuantity,
  pool.value AS poolCapacity, resolution.value AS resolutionMp,
  reqResolution.value AS requiredResolutionMp, power.value AS power,
  $quantity AS requestedQuantity,
  [{nodes:[{id:p.id,type:'PRODUCT'},{id:pool.id,type:'CAPABILITY'},
           {id:evPool.id,type:'EVIDENCE',source:evPool.source}],
    relations:['SUPPORTS','SUPPORTED_BY']},
   {nodes:[{id:p.id,type:'PRODUCT'},{id:resolution.id,type:'CAPABILITY'},
           {id:evResolution.id,type:'EVIDENCE',source:evResolution.source}],
    relations:['SUPPORTS','SUPPORTED_BY']},
   {nodes:[{id:p.id,type:'PRODUCT'},{id:power.id,type:'CAPABILITY'},
           {id:evPower.id,type:'EVIDENCE',source:evPower.source}],
    relations:['SUPPORTS','SUPPORTED_BY']}] AS evidencePaths
"""

UPS_QUERY = """
MATCH (r:REQUIREMENT {id:'REQ-UPS-SMOKE'})-[:REQUIRES]->(required:CAPABILITY {key:'capacityVaMin'})
MATCH (p:PRODUCT {id:'UPS-1500'})-[:SUPPORTS]->(actual:CAPABILITY {key:'capacityVa'})
      -[:SUPPORTED_BY]->(ev:EVIDENCE)
RETURN r.id AS requirementId, p.id AS productId,
  required.value AS requiredCapacityVa, actual.value AS capacityVa,
  [{nodes:[{id:r.id,type:'REQUIREMENT'},{id:required.id,type:'CAPABILITY'}],
    relations:['REQUIRES']},
   {nodes:[{id:p.id,type:'PRODUCT'},{id:actual.id,type:'CAPABILITY'},
           {id:ev.id,type:'EVIDENCE',source:ev.source}],
    relations:['SUPPORTS','SUPPORTED_BY']}] AS evidencePaths
"""


def _statements(path: Path) -> list[str]:
    source = "\n".join(
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("//")
    )
    return [statement.strip() for statement in source.split(";") if statement.strip()]


def _counts(conn: relate.Connection) -> dict[str, int]:
    nodes = conn.execute("MATCH (n) RETURN count(n) AS n").single()["n"]
    relationships = conn.execute("MATCH ()-[r]->() RETURN count(r) AS n").single()["n"]
    return {"nodes": nodes, "relationships": relationships}


def seed_store(store_path: Path) -> dict[str, Any]:
    """Cargar el dataset sintético; rechazar un store ajeno ya poblado."""
    if not store_path.parent.is_dir():
        raise ValueError("El directorio del store no existe")
    conn = relate.connect(str(store_path))
    try:
        if store_path.exists():
            node_count = _counts(conn)["nodes"]
            marker_count = conn.execute(
                "MATCH (e:EVIDENCE {datasetId:$dataset}) RETURN count(e) AS n",
                {"dataset": DATASET_ID},
            ).single()["n"]
            if node_count > 0 and marker_count == 0:
                raise ValueError("El store contiene datos ajenos a la demo AT-229")
        for statement in _statements(FIXTURES / "seed.cypher"):
            conn.execute(statement)
        return {"datasetId": DATASET_ID, **_counts(conn)}
    finally:
        conn.close()


def _read(
    store_path: str, query: str, params: dict[str, int] | None = None
) -> list[dict[str, Any]]:
    path = Path(store_path)
    if not path.is_file():
        raise ValueError("El store Relate no existe; ejecute seed primero")
    conn = relate.connect(str(path), read_only=True)
    try:
        return [dict(row) for row in conn.execute(query, params or {})]
    finally:
        conn.close()


def switch_evidence(store_path: str, poe_ports_min: int) -> list[dict[str, Any]]:
    """Leer sólo capacidades, ofertas y rutas fijas de switches."""
    return _read(store_path, SWITCH_QUERY, {"poe_ports_min": poe_ports_min})


def camera_stock_evidence(store_path: str, quantity: int) -> list[dict[str, Any]]:
    """Leer el pool conjunto y la evidencia técnica de CAM-POE."""
    return _read(store_path, CAMERA_QUERY, {"quantity": quantity})


def ups_evidence(store_path: str) -> list[dict[str, Any]]:
    """Leer el control de 1000 VA desde el mismo grafo."""
    return _read(store_path, UPS_QUERY)
