"""Deriva enlaces desde topología declarada; no certifica una instalación."""

from collections import defaultdict
from decimal import Decimal
from typing import Any


def _number(value: object, field: str, *, zero: bool = False) -> Decimal:
    try:
        number = Decimal(str(value))
    except (ValueError, ArithmeticError) as exc:
        raise ValueError(f"{field} inválido") from exc
    if not number.is_finite() or number < 0 or (number == 0 and not zero):
        raise ValueError(f"{field} debe ser finito y {'no negativo' if zero else 'positivo'}")
    return number


def _integer(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} debe ser entero no negativo")
    return value


def evaluate_topology(catalog: dict[str, Any], topology: dict[str, Any]) -> dict[str, Any]:
    """Evalúa enlaces requeridos, material medible y verificaciones pendientes.

    Los candidatos rechazados permanecen en el catálogo de entrada. La salida es
    técnica y no incorpora partidas a una cotización ni asigna precios.
    """
    endpoints = topology["endpoints"]
    ports = topology["ports"]
    cables = {item["id"]: item for item in catalog["cables"]}
    terminations = {item["id"]: item for item in catalog["terminations"]}
    runs = {item["id"]: item for item in topology.get("runs", [])}
    result: dict[str, Any] = {
        "status": "PENDING",
        "links": [],
        "materials": [],
        "pending": [],
        "incompatible": [],
        "validationTopics": [
            "channel_and_permanent_link_limits",
            "poe_power_budget",
            "bandwidth",
            "environment_and_uv",
            "conduit_occupancy",
            "power_separation",
            "termination_certification",
            "local_code_and_professional_review",
        ],
        "professionalValidationRequired": True,
    }
    required: list[dict[str, Any]] = []
    for endpoint in endpoints:
        medium = endpoint["medium"]
        if medium == "poe_ethernet":
            required.append(
                {
                    "id": f"LINK-{endpoint['id']}",
                    "endpointId": endpoint["id"],
                    "reason": "RULE-POE-DATA-AND-POWER",
                    "evidenceId": endpoint["evidenceId"],
                }
            )
        elif medium == "wifi_solar":
            continue
        elif medium == "mesh" and endpoint.get("wiredBackhaulRequired") is True:
            required.append(
                {
                    "id": f"LINK-{endpoint['id']}",
                    "endpointId": endpoint["id"],
                    "reason": "RULE-CONFIRMED-WIRED-BACKHAUL",
                    "evidenceId": endpoint["evidenceId"],
                }
            )
        elif medium not in ("mesh", "wifi_solar"):
            raise ValueError(f"medio desconocido: {medium}")
    if topology.get("uplinkRequired") is True:
        required.append(
            {
                "id": "LINK-UPLINK",
                "endpointId": topology["uplinkEndpointId"],
                "reason": "RULE-CONFIRMED-UPLINK",
                "evidenceId": topology["uplinkEvidenceId"],
            }
        )

    totals: dict[str, Decimal] = defaultdict(Decimal)
    cut_lengths: dict[str, list[Decimal]] = defaultdict(list)
    used_ports: set[str] = set()
    for need in required:
        link_id = need["id"]
        run = runs.get(link_id)
        link: dict[str, Any] = {
            **need,
            "status": "PENDING",
            "requiredLengthM": None,
            "cableId": None,
            "terminationIds": [],
            "evidenceIds": [need["evidenceId"]],
        }
        result["links"].append(link)
        if run is None:
            result["pending"].append(
                {
                    "linkId": link_id,
                    "field": "route_measurement",
                    "evidenceIds": [need["evidenceId"]],
                }
            )
            continue
        link["originPortId"] = run.get("originPortId")
        link["destinationPortId"] = run.get("destinationPortId")
        for side in ("originPortId", "destinationPortId"):
            port_id = run.get(side)
            if port_id is None or port_id not in ports:
                result["pending"].append(
                    {"linkId": link_id, "field": side, "evidenceIds": [need["evidenceId"]]}
                )
            elif port_id in used_ports:
                result["incompatible"].append(
                    {
                        "linkId": link_id,
                        "reason": "PORT_ALREADY_USED",
                        "portId": port_id,
                        "evidenceIds": [run["evidenceId"]],
                    }
                )
            else:
                used_ports.add(port_id)
        if run.get("destinationPortId") in ports:
            destination = ports[run["destinationPortId"]]
            if destination.get("endpointId") != need["endpointId"]:
                result["incompatible"].append(
                    {
                        "linkId": link_id,
                        "reason": "WRONG_ENDPOINT",
                        "evidenceIds": [run["evidenceId"]],
                    }
                )
        if need["reason"] == "RULE-POE-DATA-AND-POWER" and run.get("originPortId") in ports:
            source = ports[run["originPortId"]]
            if source.get("endpointId") not in ("SWITCH", "INJECTOR") or not source.get(
                "poeCapable"
            ):
                result["incompatible"].append(
                    {
                        "linkId": link_id,
                        "reason": "POE_SOURCE_PORT_REQUIRED",
                        "evidenceIds": [run["evidenceId"], need["evidenceId"]],
                    }
                )
        cable = cables.get(run.get("cableId"))
        if cable is None:
            result["pending"].append(
                {"linkId": link_id, "field": "cable_type", "evidenceIds": [run["evidenceId"]]}
            )
            continue
        link["cableId"] = cable["id"]
        link["evidenceIds"].extend([run["evidenceId"], cable["evidenceId"]])
        if cable.get("conductor") != "solid_copper" or cable.get("pairs") != 4:
            result["incompatible"].append(
                {
                    "linkId": link_id,
                    "reason": "CABLE_CONSTRUCTION",
                    "evidenceIds": [cable["evidenceId"]],
                }
            )
        environment = run.get("environment")
        if environment is None or cable.get("environment") is None:
            result["pending"].append(
                {
                    "linkId": link_id,
                    "field": "environment_compatibility",
                    "evidenceIds": [run["evidenceId"]],
                }
            )
        elif environment not in cable["environment"]:
            result["incompatible"].append(
                {
                    "linkId": link_id,
                    "reason": "CABLE_ENVIRONMENT",
                    "evidenceIds": [run["evidenceId"], cable["evidenceId"]],
                }
            )
        if run.get("pathwayId") and run.get("conduitOccupancyVerified") is not True:
            result["pending"].append(
                {
                    "linkId": link_id,
                    "field": "conduit_occupancy",
                    "evidenceIds": [run["evidenceId"]],
                }
            )
        if run.get("powerSeparationVerified") is not True:
            result["pending"].append(
                {"linkId": link_id, "field": "power_separation", "evidenceIds": [run["evidenceId"]]}
            )
        for item_id in run.get("terminationIds", []):
            item = terminations.get(item_id)
            if item is None:
                result["pending"].append(
                    {
                        "linkId": link_id,
                        "field": "termination_type",
                        "evidenceIds": [run["evidenceId"]],
                    }
                )
                continue
            link["terminationIds"].append(item_id)
            if (
                cable["category"] not in item["categories"]
                or cable["conductor"] not in item["conductors"]
            ):
                result["incompatible"].append(
                    {
                        "linkId": link_id,
                        "reason": "TERMINATION_MISMATCH",
                        "itemId": item_id,
                        "evidenceIds": [cable["evidenceId"], item["evidenceId"]],
                    }
                )
        if len(link["terminationIds"]) != 2:
            result["pending"].append(
                {"linkId": link_id, "field": "two_terminations", "evidenceIds": [run["evidenceId"]]}
            )
        sections = run.get("sectionLengthsM")
        if not run.get("routeConfirmed") or not sections:
            result["pending"].append(
                {
                    "linkId": link_id,
                    "field": "route_measurement",
                    "evidenceIds": [run["evidenceId"]],
                }
            )
            continue
        if run.get("bandwidthVerified") is not True:
            result["pending"].append(
                {"linkId": link_id, "field": "bandwidth", "evidenceIds": [run["evidenceId"]]}
            )
        if need["reason"] == "RULE-POE-DATA-AND-POWER" and run.get("poeBudgetVerified") is not True:
            result["pending"].append(
                {
                    "linkId": link_id,
                    "field": "poe_power_budget",
                    "evidenceIds": [run["evidenceId"], need["evidenceId"]],
                }
            )
        if run.get("terminationCertificationVerified") is not True:
            result["pending"].append(
                {
                    "linkId": link_id,
                    "field": "termination_certification",
                    "evidenceIds": [run["evidenceId"]],
                }
            )
        count = _integer(run.get("cableCount", 1), "cableCount")
        if count == 0:
            raise ValueError("cableCount debe ser positivo")
        route_m = sum((_number(value, "sectionLengthM") for value in sections), Decimal(0))
        slack_m = _number(run.get("slackPerEndM", 0), "slackPerEndM", zero=True)
        waste = _number(run.get("wasteFraction", 0), "wasteFraction", zero=True)
        required_m = (route_m + 2 * slack_m) * (1 + waste) * count
        link["requiredLengthM"] = str(required_m)
        totals[cable["id"]] += required_m
        cut_lengths[cable["id"]].extend([required_m / count] * count)
        if run.get("channelLimitVerified") is not True:
            result["pending"].append(
                {"linkId": link_id, "field": "channel_limit", "evidenceIds": [run["evidenceId"]]}
            )
        link["status"] = "MEASURED"

    for cable_id, length in sorted(totals.items()):
        cable = cables[cable_id]
        roll = cable.get("commercialLengthM")
        rolls = None
        purchased = None
        remainder = None
        if roll is not None:
            roll_length = _number(roll, "commercialLengthM")
            bins: list[Decimal] = []
            for cut in sorted(cut_lengths[cable_id], reverse=True):
                if cut > roll_length:
                    result["incompatible"].append(
                        {
                            "cableId": cable_id,
                            "reason": "CUT_EXCEEDS_COMMERCIAL_ROLL",
                            "evidenceIds": [cable["evidenceId"]],
                        }
                    )
                    break
                for index, remaining in enumerate(bins):
                    if remaining >= cut:
                        bins[index] -= cut
                        break
                else:
                    bins.append(roll_length - cut)
            else:
                rolls = len(bins)
                purchased = roll_length * rolls
                remainder = purchased - length
        result["materials"].append(
            {
                "cableId": cable_id,
                "requiredLengthM": str(length),
                "commercialRolls": rolls,
                "purchasedLengthM": str(purchased) if purchased is not None else None,
                "recoverableRemainderM": str(remainder) if remainder is not None else None,
                "ruleId": "RULE-SUM-CONFIRMED-ROUTES",
                "evidenceIds": sorted(
                    {
                        eid
                        for link in result["links"]
                        if link["cableId"] == cable_id and link["requiredLengthM"] is not None
                        for eid in link["evidenceIds"]
                    }
                ),
            }
        )
    result["status"] = (
        "REVIEW_REQUIRED"
        if result["incompatible"]
        else "PENDING"
        if result["pending"]
        else "DERIVED"
    )
    return result
