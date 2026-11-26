"""Seed idempotente de topología y evidencia sintéticas AT-239."""

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
fixture = json.loads((BASE / "fixture.json").read_text(encoding="utf-8"))
lines = ["// AT-239: dataset ficticio; MERGE sin borrar datos ajenos."]
for label in (
    "NETWORK_LINK",
    "ENDPOINT",
    "PORT",
    "CABLE_TYPE",
    "CABLE_RUN",
    "CONNECTOR",
    "JACK",
    "PATCH_PANEL",
    "PATCH_CORD",
    "PATHWAY",
    "CONDUIT",
    "EVIDENCE",
    "REQUIREMENT",
):
    lines.append(
        f"CREATE CONSTRAINT at239_{label.lower()}_id IF NOT EXISTS "
        f"FOR (n:{label}) REQUIRE n.id IS UNIQUE;"
    )


def lit(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def node(label: str, ident: str, **props: object) -> None:
    values = ", ".join(
        f"{key}: {lit(value)}"
        for key, value in {"datasetId": fixture["datasetId"], **props}.items()
    )
    lines.append(f"MERGE (n:{label} {{id: {lit(ident)}}}) SET n += {{{values}}};")


def edge(source: tuple[str, str], relation: str, target: tuple[str, str], rule: str) -> None:
    a_label, a_id = source
    b_label, b_id = target
    lines.append(
        f"MATCH (a:{a_label} {{id: {lit(a_id)}}}), (b:{b_label} {{id: {lit(b_id)}}}) "
        f"MERGE (a)-[:{relation} {{ruleId: {lit(rule)}}}]->(b);"
    )


for endpoint in fixture["topology"]["endpoints"]:
    node("ENDPOINT", endpoint["id"], medium=endpoint["medium"])
    node("EVIDENCE", endpoint["evidenceId"], kind="synthetic_topology")
    edge(
        ("ENDPOINT", endpoint["id"]),
        "SUPPORTED_BY",
        ("EVIDENCE", endpoint["evidenceId"]),
        "RULE-INPUT",
    )
for port_id, port in fixture["topology"]["ports"].items():
    node("PORT", port_id, poeCapable=port["poeCapable"])
    if port["endpointId"] != "SWITCH":
        edge(("ENDPOINT", port["endpointId"]), "CONNECTS_TO", ("PORT", port_id), "RULE-PORT-OWNER")
node("ENDPOINT", "SWITCH", medium="switch")
node("REQUIREMENT", "REQ-POE-CABLE", kind="poe_cable")
node("REQUIREMENT", "REQ-CAT6", kind="category")
for cable in fixture["catalog"]["cables"]:
    node("CABLE_TYPE", cable["id"], category=cable["category"], conductor=cable["conductor"])
    node("EVIDENCE", cable["evidenceId"], kind="synthetic_catalog")
    edge(
        ("CABLE_TYPE", cable["id"]),
        "SUPPORTED_BY",
        ("EVIDENCE", cable["evidenceId"]),
        "RULE-CATALOG",
    )
    if cable["conductor"] == "solid_copper":
        edge(
            ("CABLE_TYPE", cable["id"]),
            "SUPPORTS_POE",
            ("REQUIREMENT", "REQ-POE-CABLE"),
            "RULE-SYNTHETIC-CAPABILITY",
        )
    edge(
        ("CABLE_TYPE", cable["id"]),
        "SUPPORTS_STANDARD",
        ("REQUIREMENT", "REQ-CAT6"),
        "RULE-CATALOG-CATEGORY",
    )
for item in fixture["catalog"]["terminations"]:
    label = "JACK" if item["kind"] == "jack" else "CONNECTOR"
    node(label, item["id"], kind=item["kind"])
    node("EVIDENCE", item["evidenceId"], kind="synthetic_catalog")
    edge((label, item["id"]), "SUPPORTED_BY", ("EVIDENCE", item["evidenceId"]), "RULE-CATALOG")
node("PATHWAY", "PATH-EMT-DEMO", kind="conduit")
node("CONDUIT", "CONDUIT-EMT-DEMO", kind="emt")
edge(
    ("PATHWAY", "PATH-EMT-DEMO"), "SHARES_PATHWAY", ("CONDUIT", "CONDUIT-EMT-DEMO"), "RULE-PATHWAY"
)
for endpoint in fixture["topology"]["endpoints"]:
    if endpoint["medium"] == "poe_ethernet" or endpoint.get("wiredBackhaulRequired") is True:
        link_id = f"LINK-{endpoint['id']}"
        node("NETWORK_LINK", link_id, state="required")
        edge(
            ("ENDPOINT", endpoint["id"]),
            "REQUIRES_LINK",
            ("NETWORK_LINK", link_id),
            "RULE-TOPOLOGY",
        )
        edge(
            ("NETWORK_LINK", link_id),
            "SUPPORTED_BY",
            ("EVIDENCE", endpoint["evidenceId"]),
            "RULE-TOPOLOGY",
        )
node("NETWORK_LINK", "LINK-UPLINK", state="required")
node("EVIDENCE", "EV-UPLINK", kind="synthetic_topology")
edge(
    ("ENDPOINT", "ROUTER"),
    "REQUIRES_LINK",
    ("NETWORK_LINK", "LINK-UPLINK"),
    "RULE-CONFIRMED-UPLINK",
)
edge(
    ("NETWORK_LINK", "LINK-UPLINK"),
    "SUPPORTED_BY",
    ("EVIDENCE", "EV-UPLINK"),
    "RULE-CONFIRMED-UPLINK",
)
for run in fixture["topology"]["runs"]:
    node("CABLE_RUN", run["id"], confirmed=run["routeConfirmed"])
    node("EVIDENCE", run["evidenceId"], kind="synthetic_route")
    edge(("NETWORK_LINK", run["id"]), "CONNECTS_TO", ("CABLE_RUN", run["id"]), "RULE-RUN")
    edge(
        ("CABLE_RUN", run["id"]),
        "USES_CABLE",
        ("CABLE_TYPE", run["cableId"]),
        "RULE-SELECTED-CABLE",
    )
    edge(
        ("CABLE_RUN", run["id"]),
        "SUPPORTED_BY",
        ("EVIDENCE", run["evidenceId"]),
        "RULE-ROUTE-INPUT",
    )
    for port_id in (run["originPortId"], run["destinationPortId"]):
        edge(("CABLE_RUN", run["id"]), "CONNECTS_TO", ("PORT", port_id), "RULE-RUN-PORT")
    for item_id in run["terminationIds"]:
        label = "JACK" if item_id.startswith("JACK") else "CONNECTOR"
        edge(("CABLE_RUN", run["id"]), "TERMINATES_AT", (label, item_id), "RULE-TERMINATION")
        edge(
            ("NETWORK_LINK", run["id"]),
            "REQUIRES_CONNECTOR",
            (label, item_id),
            "RULE-TERMINATION-DEPENDENCY",
        )
    if run.get("pathwayId"):
        edge(
            ("CABLE_RUN", run["id"]),
            "ROUTED_THROUGH",
            ("PATHWAY", "PATH-EMT-DEMO"),
            "RULE-CONFIRMED-PATHWAY",
        )

(BASE / "seed.cypher").write_text("\n".join(lines) + "\n", encoding="utf-8")
