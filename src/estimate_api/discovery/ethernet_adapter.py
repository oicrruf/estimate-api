"""Typed AT-239 topology result; unmeasured links remain explicit requirements."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from math import isfinite
from typing import Any, Literal, cast

from estimate_api.ethernet.evaluate import evaluate_topology

from .models import Proposal, ProposalLine


def _reviewable_length(value: str) -> float:
    """Reject finite Decimal lengths that cannot be represented as positive JSON numbers."""
    try:
        decimal = Decimal(value)
        quantity = float(decimal)
    except (InvalidOperation, OverflowError, ValueError) as error:
        raise ValueError("Topology length is not reviewable") from error
    if not decimal.is_finite() or decimal <= 0 or not isfinite(quantity) or quantity <= 0:
        raise ValueError("Topology length is not reviewable")
    return quantity


@dataclass(frozen=True)
class TopologyLink:
    id: str
    status: str
    reason: str
    required_length_m: str | None
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class TopologyMaterial:
    cable_id: str
    required_length_m: str
    commercial_rolls: int | None
    rule_id: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class TopologyScope:
    status: Literal["PENDING", "REVIEW_REQUIRED", "DERIVED"]
    links: tuple[TopologyLink, ...]
    materials: tuple[TopologyMaterial, ...]
    pending: tuple[str, ...]
    incompatible: tuple[str, ...]
    professional_validation_required: bool
    material_totals_complete: bool


def evaluate_ethernet_scope(catalog: dict[str, Any], topology: dict[str, Any]) -> TopologyScope:
    raw = evaluate_topology(catalog, topology)
    if raw["status"] not in ("PENDING", "REVIEW_REQUIRED", "DERIVED"):
        raise ValueError("Unknown AT-239 status")
    for link in raw["links"]:
        if link["requiredLengthM"] is not None:
            _reviewable_length(str(link["requiredLengthM"]))
    for material in raw["materials"]:
        _reviewable_length(str(material["requiredLengthM"]))
    totals_complete = all(item["requiredLengthM"] is not None for item in raw["links"])
    return TopologyScope(
        status=cast(Literal["PENDING", "REVIEW_REQUIRED", "DERIVED"], raw["status"]),
        links=tuple(
            TopologyLink(
                str(item["id"]),
                str(item["status"]),
                str(item["reason"]),
                str(item["requiredLengthM"]) if item["requiredLengthM"] is not None else None,
                tuple(item["evidenceIds"]),
            )
            for item in raw["links"]
        ),
        materials=tuple(
            TopologyMaterial(
                str(item["cableId"]),
                str(item["requiredLengthM"]),
                item["commercialRolls"] if totals_complete else None,
                str(item["ruleId"]),
                tuple(item["evidenceIds"]),
            )
            for item in raw["materials"]
        ),
        pending=tuple(f"{item['linkId']}:{item['field']}" for item in raw["pending"]),
        incompatible=tuple(str(item["reason"]) for item in raw["incompatible"]),
        professional_validation_required=bool(raw["professionalValidationRequired"]),
        material_totals_complete=totals_complete,
    )


def attach_topology_links(proposal: Proposal, topology: TopologyScope) -> Proposal:
    """Add all required links to review, including links with unknown lengths."""
    for link in topology.links:
        if link.required_length_m is not None:
            _reviewable_length(link.required_length_m)
    for material in topology.materials:
        _reviewable_length(material.required_length_m)
    existing = {line.key for line in proposal.lines}
    if any(link.id in existing for link in topology.links):
        raise ValueError("Topology link collides with existing proposal line")
    link_additions = tuple(
        ProposalLine(
            key=link.id,
            kind=None,
            work_package="ethernet",
            quantity=1,
            unit="link",
            state="agent_proposed",
            required=True,
            justification=link.reason,
            rule_id=link.reason,
            source="AT-239 topology",
            package_version="1.0.0",
            jurisdiction=None,
            parent_key=None,
            relation="CONNECTS_TO",
            evidence_ids=link.evidence_ids,
            rule_ids=(link.reason,),
            source_refs=("AT-239",),
        )
        for link in topology.links
    )
    material_additions = tuple(
        ProposalLine(
            key=f"at239:cable:{material.cable_id}",
            kind="material",
            work_package="ethernet",
            quantity=_reviewable_length(material.required_length_m)
            if topology.material_totals_complete
            else None,
            unit="m",
            state="agent_proposed" if topology.material_totals_complete else "pending_measurement",
            required=True,
            justification="Longitud parcial medida; falta confirmar todos los enlaces"
            if not topology.material_totals_complete
            else "Longitud derivada de rutas confirmadas",
            rule_id=material.rule_id,
            source="AT-239 topology",
            package_version="1.0.0",
            jurisdiction=None,
            parent_key=None,
            relation="REQUIRES",
            evidence_ids=material.evidence_ids,
            rule_ids=(material.rule_id,),
            source_refs=("AT-239",),
        )
        for material in topology.materials
    )
    additions = (*link_additions, *material_additions)
    if any(line.key in existing for line in additions):
        raise ValueError("Topology material collides with existing proposal line")
    questions = tuple(
        dict.fromkeys(
            (
                *proposal.questions,
                *(f"Confirmar enlace {item}" for item in topology.pending),
                *(
                    "Confirmar longitudes de todos los enlaces antes de totalizar cable"
                    for _ in range(0 if topology.material_totals_complete else 1)
                ),
            )
        )
    )
    partial = ("ethernet_material_totals",) if not topology.material_totals_complete else ()
    blocking = tuple(dict.fromkeys((*proposal.blocking_facts, *topology.pending, *partial)))
    technical_blockers = tuple(
        dict.fromkeys((*proposal.technical_blockers, *topology.incompatible))
    )
    status: Literal["blocked", "proposed", "pending_specialist"] = (
        "blocked"
        if topology.incompatible
        else (proposal.status if proposal.status == "pending_specialist" else "proposed")
    )
    return replace(
        proposal,
        lines=(*proposal.lines, *additions),
        questions=questions,
        blocking_facts=blocking,
        technical_blockers=technical_blockers,
        status=status,
        commercial_ready=False,
        work_packages={**proposal.work_packages, "ethernet": "pending"},
    )
