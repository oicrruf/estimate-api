"""Genera un seed Relate aislado desde la fixture pública ficticia."""

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
data = json.loads((BASE / "fixture.json").read_text(encoding="utf-8"))


def lit(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


lines = ["// Grafo ficticio AT-238. MERGE por ID; sin borrado de otros datos."]
for label in (
    "INSTALLATION_SEGMENT",
    "MATERIAL",
    "ACCESSORY",
    "ENCLOSURE",
    "REQUIREMENT",
    "SPEC",
    "EVIDENCE",
):
    lines.append(
        f"CREATE CONSTRAINT at238_{label.lower()}_id IF NOT EXISTS "
        f"FOR (n:{label}) REQUIRE n.id IS UNIQUE;"
    )


def node(label: str, ident: str, props: dict[str, str]) -> None:
    values = ", ".join(f"{key}: {lit(value)}" for key, value in props.items())
    lines.append(f"MERGE (n:{label} {{id: {lit(ident)}}}) SET n += {{{values}}};")


def edge(a_label: str, a_id: str, rel: str, b_label: str, b_id: str, rule: str) -> None:
    lines.append(
        f"MATCH (a:{a_label} {{id: {lit(a_id)}}}), "
        f"(b:{b_label} {{id: {lit(b_id)}}}) "
        f"MERGE (a)-[r:{rel} {{ruleId: {lit(rule)}}}]->(b);"
    )


for route in data["routes"].values():
    node("INSTALLATION_SEGMENT", route["id"], {"id": route["id"], "datasetId": data["datasetId"]})
    node(
        "EVIDENCE",
        route["evidenceId"],
        {"id": route["evidenceId"], "kind": "synthetic_route_input"},
    )
    edge(
        "INSTALLATION_SEGMENT",
        route["id"],
        "SUPPORTED_BY",
        "EVIDENCE",
        route["evidenceId"],
        "RULE-CONFIRMED-INPUT",
    )

node("ENCLOSURE", "BOX-DEMO", {"id": "BOX-DEMO", "kind": "generic_box"})
for family in ("coupling", "connector", "support"):
    req_id = f"REQ-DEMO-{family.upper()}"
    node("REQUIREMENT", req_id, {"id": req_id, "family": family})
    edge(
        "INSTALLATION_SEGMENT",
        "SEG-DEMO",
        "REQUIRES",
        "REQUIREMENT",
        req_id,
        f"RULE-CONFIRMED-{family.upper()}",
    )
    edge(
        "REQUIREMENT",
        req_id,
        "SUPPORTED_BY",
        "EVIDENCE",
        "EV-ROUTE-CONFIRMED",
        "RULE-CONFIRMED-INPUT",
    )

for diameter in ("1", "3/4"):
    spec_id = f"SPEC-DIAMETER-{diameter.replace('/', '-')}"
    node("SPEC", spec_id, {"id": spec_id, "diameter": diameter})
    for item in data["catalog"]["items"]:
        if item.get("diameter") != diameter:
            continue
        label = "MATERIAL" if item["family"] == "emt" else "ACCESSORY"
        node(
            label, item["id"], {"id": item["id"], "family": item["family"], "kind": "generic_type"}
        )
        node(
            "EVIDENCE",
            item["evidenceId"],
            {"id": item["evidenceId"], "kind": "synthetic_catalog_record"},
        )
        edge(label, item["id"], "FITS_DIAMETER", "SPEC", spec_id, "RULE-CATALOG-DIAMETER")
        edge(
            label,
            item["id"],
            "SUPPORTED_BY",
            "EVIDENCE",
            item["evidenceId"],
            "RULE-CATALOG-EVIDENCE",
        )

node("ACCESSORY", "GEN-OUTLET", {"id": "GEN-OUTLET", "family": "outlet", "kind": "generic_type"})
node("EVIDENCE", "EV-CAT-OUTLET", {"id": "EV-CAT-OUTLET", "kind": "synthetic_catalog_record"})
edge(
    "ACCESSORY", "GEN-OUTLET", "SUPPORTED_BY", "EVIDENCE", "EV-CAT-OUTLET", "RULE-CATALOG-EVIDENCE"
)
edge(
    "INSTALLATION_SEGMENT",
    "SEG-DEMO",
    "CONNECTS_TO",
    "ENCLOSURE",
    "BOX-DEMO",
    "RULE-CONFIRMED-ENTRIES",
)
for diameter in ("1", "3/4"):
    suffix = "1" if diameter == "1" else "3-4"
    edge(
        "ACCESSORY",
        f"GEN-CONNECTOR-{suffix}",
        "CONNECTS_TO",
        "ENCLOSURE",
        "BOX-DEMO",
        "RULE-CATALOG-CONNECTOR",
    )
    edge(
        "ACCESSORY",
        f"GEN-SUPPORT-{suffix}",
        "MOUNTS_TO",
        "INSTALLATION_SEGMENT",
        "SEG-DEMO",
        "RULE-CATALOG-SUPPORT",
    )
for family in ("COUPLING", "CONNECTOR", "SUPPORT"):
    edge(
        "ACCESSORY",
        f"GEN-{family}-1",
        "ALTERNATIVE_TO",
        "ACCESSORY",
        f"GEN-{family}-3-4",
        "RULE-DIAMETER-ALTERNATIVE",
    )

(BASE / "seed.cypher").write_text("\n".join(lines) + "\n", encoding="utf-8")
