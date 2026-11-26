"""Deriva sólo desde observaciones confirmadas; no valida diseño eléctrico."""

from dataclasses import asdict, dataclass
from decimal import ROUND_CEILING, Decimal
from typing import Any


@dataclass(frozen=True)
class Line:
    material_id: str
    family: str
    quantity: int
    unit: str
    rule_id: str
    evidence_ids: tuple[str, ...]


def _positive(value: object, name: str) -> Decimal:
    result = Decimal(str(value))
    if not result.is_finite() or result <= 0:
        raise ValueError(f"{name} debe ser positivo y finito")
    return result


def _count(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} debe ser entero no negativo")
    return value


def evaluate_route(catalog: dict[str, Any], route: dict[str, Any]) -> dict[str, Any]:
    """Evalúa tipos genéricos y conserva la procedencia de cada cantidad."""
    validation = [
        "capacidad_y_llenado",
        "ambiente_y_accesibilidad",
        "fijacion_y_separacion",
        "puesta_a_tierra_y_proteccion",
        "normativa_local",
    ]
    if not route.get("confirmed", False):
        return {
            "status": "PENDING",
            "lines": [],
            "missing": [],
            "incompatible": [],
            "pending": [
                "route_topology",
                "section_lengths",
                "diameter",
                "terminations",
                "supports",
            ],
            "professionalValidationRequired": True,
            "validationTopics": validation,
        }

    evidence = route["evidenceId"]
    diameter = route["diameter"]
    items = catalog["items"]
    by_id = {item["id"]: item for item in items}
    emt = next(item for item in items if item["family"] == "emt" and item["diameter"] == diameter)
    commercial = _positive(emt["commercialLengthM"], "commercialLengthM")
    waste = Decimal(str(route.get("wasteFraction", "0")))
    if not waste.is_finite() or waste < 0:
        raise ValueError("wasteFraction debe ser no negativo y finito")
    lengths = route["sectionLengthsM"]
    if not lengths:
        raise ValueError("La ruta confirmada requiere secciones medidas")
    pieces = sum(
        int(
            ((_positive(length, "sectionLengthM") * (1 + waste)) / commercial).to_integral_value(
                rounding=ROUND_CEILING
            )
        )
        for length in lengths
    )
    lines = [
        Line(
            emt["id"],
            "emt",
            pieces,
            "piece",
            "RULE-COMMERCIAL-SECTION",
            (evidence, emt["evidenceId"]),
        )
    ]
    missing: list[dict[str, Any]] = []
    incompatible: list[dict[str, Any]] = []
    selected: dict[str, str] = route.get("selectedAccessories", {})
    quantities = {
        "coupling": (route["confirmedJoins"], "RULE-CONFIRMED-JOINS"),
        "connector": (route["confirmedBoxEntries"], "RULE-CONFIRMED-ENTRIES"),
        "support": (route["confirmedSupportPoints"], "RULE-CONFIRMED-SUPPORTS"),
    }
    if route.get("lbRequired") is True:
        quantities["lb"] = (route["confirmedLbPoints"], "RULE-CONFIRMED-LB")
    if route.get("interiorOutletRequired") is True:
        quantities["outlet"] = (route["confirmedOutletPoints"], "RULE-CONFIRMED-OUTLET")
    for family, (raw_quantity, rule) in quantities.items():
        quantity = _count(raw_quantity, family)
        if quantity == 0:
            continue
        eligible = [
            item
            for item in items
            if item["family"] == family and item.get("diameter") in (diameter, None)
        ]
        alternatives = [{"id": item["id"], "evidenceId": item["evidenceId"]} for item in eligible]
        selected_id = selected.get(family)
        chosen = by_id.get(selected_id) if selected_id else None
        if chosen and (
            chosen["family"] != family or chosen.get("diameter") not in (diameter, None)
        ):
            incompatible.append(
                {
                    "id": selected_id,
                    "family": family,
                    "reason": "DIAMETER_OR_FAMILY_MISMATCH",
                    "evidenceIds": [evidence, chosen["evidenceId"]],
                    "alternatives": alternatives,
                }
            )
            chosen = None
        if chosen is None:
            missing.append(
                {
                    "family": family,
                    "quantity": quantity,
                    "ruleId": rule,
                    "evidenceIds": [evidence],
                    "alternatives": alternatives,
                }
            )
        else:
            lines.append(
                Line(
                    chosen["id"], family, quantity, "piece", rule, (evidence, chosen["evidenceId"])
                )
            )
    return {
        "status": "REVIEW_REQUIRED" if missing or incompatible else "DERIVED",
        "lines": [asdict(line) for line in lines],
        "missing": missing,
        "incompatible": incompatible,
        "pending": validation,
        "professionalValidationRequired": True,
        "validationTopics": validation,
    }
