"""Route confirmed scope to specialists without deriving a bill of materials.

The discovery engine owns proposals. This module owns only evidence questions and
deduplicated work assignments; callers must verify the returned facts separately.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Literal, cast

from estimate_api.domain.scope_capture.contract import Certainty, Fact

Specialty = Literal["cameras", "networks", "raceway"]
CameraMedium = Literal["poe_ethernet", "analog_coax", "wifi"]


@dataclass(frozen=True)
class CameraScope:
    medium: CameraMedium
    count: Fact[int] | None
    existing_switch_model: Fact[str] | None = None
    existing_switch_poe_w: Fact[float] | None = None
    existing_switch_free_ports: Fact[int] | None = None
    existing_uplink_adequate: Fact[bool] | None = None
    existing_wifi_capacity_verified: Fact[bool] | None = None


@dataclass(frozen=True)
class RacewayScope:
    route_id: str
    linked_to_camera: bool = False
    route_length_m: Fact[float] | None = None
    capacity_verified: Fact[bool] | None = None
    cable_outer_diameter_mm: Fact[float] | None = None


@dataclass(frozen=True)
class RoutingRequest:
    project_id: str
    cameras: CameraScope | None = None
    raceways: tuple[RacewayScope, ...] = ()
    explicit_specialties: tuple[Specialty, ...] = ()


@dataclass(frozen=True)
class Assignment:
    specialty: Specialty
    key: str
    evidence_dependencies: tuple[str, ...]


@dataclass(frozen=True)
class RoutingResult:
    assignments: tuple[Assignment, ...]
    questions: tuple[str, ...]
    invalidated_evidence: tuple[str, ...]
    proposed_lines: tuple[()] = ()


def _confirmed(value: Fact[Any] | None) -> Any:
    return value.value if value is not None and value.certainty == Certainty.CONFIRMED else None


def _positive_number(value: object) -> bool:
    if type(value) not in (int, float):
        return False
    number = cast(int | float, value)
    return isfinite(number) and number > 0


def route_specialties(
    request: RoutingRequest, *, previous: RoutingRequest | None = None
) -> RoutingResult:
    """Coordinate known paths; unknowns yield questions, never purchases."""
    if not request.project_id.strip():
        raise ValueError("project_id is required")
    if previous is not None and previous.project_id != request.project_id:
        raise ValueError("previous scope belongs to another project")
    assignments: dict[tuple[Specialty, str], Assignment] = {}
    questions: list[str] = []
    invalidated: set[str] = set()

    def assign(specialty: Specialty, key: str, *deps: str) -> None:
        assignments[(specialty, key)] = Assignment(specialty, key, deps)

    camera = request.cameras
    prior_camera = previous.cameras if previous is not None else None
    if camera is not None:
        assign("cameras", "camera-scope", "camera:medium", "camera:count")
        count = _confirmed(camera.count)
        if type(count) is not int or count <= 0:
            questions.append("Confirm the camera count with evidence.")
            count = None
        if camera.medium == "poe_ethernet":
            assign("networks", "poe-uplink", "camera:count", "network:switch")
            model = _confirmed(camera.existing_switch_model)
            if not isinstance(model, str) or not model.strip():
                questions.append("Confirm the existing switch model.")
            power = _confirmed(camera.existing_switch_poe_w)
            if not _positive_number(power):
                questions.append("Confirm the existing switch PoE power budget.")
            ports = _confirmed(camera.existing_switch_free_ports)
            if type(ports) is not int or ports < 0:
                questions.append("Confirm the existing switch free PoE ports.")
            elif count is not None and ports < count:
                questions.append("Resolve the confirmed PoE port shortfall.")
        elif camera.medium == "analog_coax":
            uplink = _confirmed(camera.existing_uplink_adequate)
            if uplink is not True:
                assign("networks", "dvr-uplink-review", "network:uplink")
                questions.append(
                    "Resolve the inadequate DVR uplink."
                    if uplink is False
                    else "Confirm whether the existing DVR uplink is adequate."
                )
        elif camera.medium == "wifi":
            assign("networks", "wifi-capacity-review", "camera:count", "network:wifi-capacity")
            wifi_capacity = _confirmed(camera.existing_wifi_capacity_verified)
            if wifi_capacity is not True:
                questions.append(
                    "Resolve insufficient existing Wi-Fi capacity."
                    if wifi_capacity is False
                    else "Confirm existing Wi-Fi capacity with evidence."
                )
        else:
            raise ValueError("unknown camera medium")
        if prior_camera is not None:
            if prior_camera.medium != camera.medium:
                invalidated.add("camera:medium")
            if prior_camera.count != camera.count:
                invalidated.add("camera:count")
            if (prior_camera.medium != camera.medium or prior_camera.count != camera.count) and (
                camera.medium == "poe_ethernet" or prior_camera.medium == "poe_ethernet"
            ):
                invalidated.add("network:poe-link")
            if camera.medium == "poe_ethernet" and (
                prior_camera.existing_switch_model != camera.existing_switch_model
                or prior_camera.existing_switch_poe_w != camera.existing_switch_poe_w
                or prior_camera.existing_switch_free_ports != camera.existing_switch_free_ports
            ):
                invalidated.add("network:switch")
                invalidated.add("network:poe-link")
            if prior_camera.existing_uplink_adequate != camera.existing_uplink_adequate:
                invalidated.add("network:uplink")
            if (
                prior_camera.existing_wifi_capacity_verified
                != camera.existing_wifi_capacity_verified
            ):
                invalidated.add("network:wifi-capacity")
    elif prior_camera is not None:
        invalidated.update(("camera:scope", "camera:count"))
        if prior_camera.medium == "poe_ethernet":
            invalidated.add("network:poe-link")

    prior_routes = {r.route_id: r for r in previous.raceways} if previous else {}
    seen_routes: set[str] = set()
    for route in request.raceways:
        if not route.route_id.strip() or route.route_id in seen_routes:
            raise ValueError("route ids must be unique and nonempty")
        seen_routes.add(route.route_id)
        key = f"raceway:{route.route_id}"
        assign("raceway", route.route_id, f"{key}:route", f"{key}:capacity", f"{key}:od")
        length = _confirmed(route.route_length_m)
        if not _positive_number(length):
            questions.append(f"Confirm measured route for {route.route_id}.")
        if _confirmed(route.capacity_verified) is not True:
            questions.append(f"Confirm raceway capacity for {route.route_id}.")
        od = _confirmed(route.cable_outer_diameter_mm)
        if not _positive_number(od):
            questions.append(f"Confirm cable outer diameter for {route.route_id}.")
        prior = prior_routes.get(route.route_id)
        if prior is not None and prior.linked_to_camera != route.linked_to_camera:
            invalidated.add(f"{key}:link")
        if (
            route.linked_to_camera
            and prior_camera is not None
            and (
                camera is None
                or prior_camera.count != camera.count
                or prior_camera.medium != camera.medium
            )
        ):
            invalidated.add(f"{key}:link")
        if prior is not None:
            if prior.route_length_m != route.route_length_m:
                invalidated.add(f"{key}:route")
            if prior.capacity_verified != route.capacity_verified:
                invalidated.add(f"{key}:capacity")
            if prior.cable_outer_diameter_mm != route.cable_outer_diameter_mm:
                invalidated.add(f"{key}:od")
                invalidated.add(f"{key}:link")
    for removed in prior_routes.keys() - seen_routes:
        invalidated.add(f"raceway:{removed}:route")
        invalidated.add(f"raceway:{removed}:link")
    for specialty in request.explicit_specialties:
        if specialty not in ("cameras", "networks", "raceway"):
            raise ValueError("unknown specialty")
        if not any(item.specialty == specialty for item in assignments.values()):
            assign(specialty, "explicit")
    return RoutingResult(
        tuple(assignments.values()), tuple(dict.fromkeys(questions)), tuple(sorted(invalidated))
    )
