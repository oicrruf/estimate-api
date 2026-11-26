#!/usr/bin/env python3
"""Genera seed.cypher determinista desde datos ficticios; no usa servicios externos."""

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = json.loads((BASE / "evidence-graph.json").read_text(encoding="utf-8"))


def literal(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, int | float):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(map(literal, value)) + "]"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{key}: {literal(val)}" for key, val in value.items()) + "}"
    raise TypeError(type(value))


lines = [
    "// DATOS Y PRECIOS FICTICIOS. Ejecutar en base local vacía o de demostración.",
    "// Idempotente para los IDs estimate-hackathon-v1; no borra otros datos.",
]
for label in ("REQUIREMENT", "PRODUCT", "CAPABILITY", "OFFER", "EVIDENCE", "ACCESSORY"):
    lines.append(
        f"CREATE CONSTRAINT {label.lower()}_id IF NOT EXISTS "
        f"FOR (n:{label}) REQUIRE n.id IS UNIQUE;"
    )


def node(label, id_, props):
    lines.append(f"MERGE (n:{label} {{id: {literal(id_)}}}) SET n += {literal(props)};")


def relation(from_label, from_id, rel, to_label, to_id):
    lines.append(
        f"MATCH (a:{from_label} {{id: {literal(from_id)}}}), "
        f"(b:{to_label} {{id: {literal(to_id)}}}) "
        f"MERGE (a)-[:{rel}]->(b);"
    )


for req in DATA["requirements"]:
    node("REQUIREMENT", req["id"], {k: v for k, v in req.items() if k != "constraints"})
    for key, val in req["constraints"].items():
        cap_id = f"{req['id']}:{key}"
        node("CAPABILITY", cap_id, {"id": cap_id, "key": key, "value": val, "role": "required"})
        relation("REQUIREMENT", req["id"], "REQUIRES", "CAPABILITY", cap_id)

for evidence in DATA["evidence"]:
    node(
        "EVIDENCE",
        evidence["id"],
        {"id": evidence["id"], "source": evidence["source"], "datasetId": DATA["datasetId"]},
    )

technical_evidence = {
    evidence["productId"]: evidence["id"]
    for evidence in DATA["evidence"]
    if evidence["id"] != "EV-POOL-CAM"
}

for product in DATA["products"]:
    props = {k: v for k, v in product.items() if k not in ("capabilities", "requiredAccessories")}
    node("PRODUCT", product["id"], props)
    evidence_id = technical_evidence[product["id"]]
    for key, val in product["capabilities"].items():
        cap_id = f"{product['id']}:{key}"
        node("CAPABILITY", cap_id, {"id": cap_id, "key": key, "value": val, "role": "measured"})
        relation("PRODUCT", product["id"], "SUPPORTS", "CAPABILITY", cap_id)
        relation("CAPABILITY", cap_id, "SUPPORTED_BY", "EVIDENCE", evidence_id)
    if "poolCapacity" in product:
        cap_id = f"{product['id']}:poolCapacity"
        node(
            "CAPABILITY",
            cap_id,
            {
                "id": cap_id,
                "key": "poolCapacity",
                "value": product["poolCapacity"],
                "role": "measured",
            },
        )
        relation("PRODUCT", product["id"], "SUPPORTS", "CAPABILITY", cap_id)
        relation("CAPABILITY", cap_id, "SUPPORTED_BY", "EVIDENCE", "EV-POOL-CAM")

for item in DATA["accessories"]:
    node("ACCESSORY", item["id"], item)
for product in DATA["products"]:
    for acc_id in product.get("requiredAccessories", []):
        relation("PRODUCT", product["id"], "REQUIRES_ACCESSORY", "ACCESSORY", acc_id)
        relation("ACCESSORY", acc_id, "SUPPORTED_BY", "EVIDENCE", technical_evidence[product["id"]])

for offer in DATA["offers"]:
    node("OFFER", offer["id"], offer)
    relation("OFFER", offer["id"], "SELLS", "PRODUCT", offer["productId"])

for product_id, req_id, reason in (
    ("SW-8", "REQ-SWITCH", "TOTAL_PORTS_8_LT_9"),
    ("CAM-12V", "REQ-CAMERA", "POWER_NOT_POE"),
    ("UPS-600", "REQ-UPS-SMOKE", "CAPACITY_600_LT_1000"),
):
    lines.append(
        f"MATCH (p:PRODUCT {{id: {literal(product_id)}}}), "
        f"(r:REQUIREMENT {{id: {literal(req_id)}}}) "
        f"MERGE (p)-[x:INCOMPATIBLE_WITH]->(r) SET x.reasonCode = {literal(reason)};"
    )

lines.append("// Fin del seed ficticio.")
(BASE / "seed.cypher").write_text("\n".join(lines) + "\n", encoding="utf-8")
