"""Synthetic routing checks at the pure coordinator entry point."""

from dataclasses import replace

import pytest

from estimate_api.domain.scope_capture.contract import Certainty, Fact
from estimate_api.specialties.routing import (
    CameraScope,
    RacewayScope,
    RoutingRequest,
    route_specialties,
)


def confirmed[T](value: T) -> Fact[T]:
    return Fact(value, Certainty.CONFIRMED, "synthetic:confirmed")


def keys(result: object) -> set[tuple[str, str]]:
    return {(a.specialty, a.key) for a in result.assignments}  # type: ignore[attr-defined]


def test_explicit_raceway_unknown_route_and_capacity_ask_without_lines() -> None:
    result = route_specialties(
        RoutingRequest("p", raceways=(RacewayScope("north"),), explicit_specialties=("raceway",))
    )
    assert keys(result) == {("raceway", "north")}
    assert len(result.questions) == 3
    assert result.proposed_lines == ()


def test_poe_existing_switch_unknown_requires_evidence_without_purchase() -> None:
    result = route_specialties(
        RoutingRequest("p", cameras=CameraScope("poe_ethernet", confirmed(8)))
    )
    assert keys(result) == {("cameras", "camera-scope"), ("networks", "poe-uplink")}
    assert "Confirm the existing switch model." in result.questions
    assert "Confirm the existing switch PoE power budget." in result.questions
    assert "Confirm the existing switch free PoE ports." in result.questions
    assert result.proposed_lines == ()


def test_analog_coax_with_adequate_dvr_uplink_has_no_poe_network_assignment() -> None:
    result = route_specialties(
        RoutingRequest(
            "p",
            cameras=CameraScope(
                "analog_coax", confirmed(4), existing_uplink_adequate=confirmed(True)
            ),
        )
    )
    assert keys(result) == {("cameras", "camera-scope")}
    assert result.questions == ()
    assert result.proposed_lines == ()


def test_count_and_od_changes_invalidate_only_relevant_evidence() -> None:
    camera = CameraScope("poe_ethernet", confirmed(4))
    routes = (
        RacewayScope("camera", True, confirmed(20.0), confirmed(True), confirmed(6.0)),
        RacewayScope("other", False, confirmed(5.0), confirmed(True), confirmed(4.0)),
    )
    before = RoutingRequest("p", camera, routes)
    after = replace(before, cameras=replace(camera, count=confirmed(6)))
    changed = route_specialties(after, previous=before)
    assert changed.invalidated_evidence == (
        "camera:count",
        "network:poe-link",
        "raceway:camera:link",
    )
    changed_route = replace(routes[0], cable_outer_diameter_mm=confirmed(7.0))
    changed = route_specialties(
        replace(before, raceways=(changed_route, routes[1])), previous=before
    )
    assert changed.invalidated_evidence == ("raceway:camera:link", "raceway:camera:od")
    assert len(keys(changed)) == len(changed.assignments)


def test_unknown_and_confirmed_inadequate_uplink_are_distinct() -> None:
    unknown = route_specialties(RoutingRequest("p", CameraScope("analog_coax", confirmed(2))))
    inadequate = route_specialties(
        RoutingRequest(
            "p", CameraScope("analog_coax", confirmed(2), existing_uplink_adequate=confirmed(False))
        )
    )
    assert (
        keys(unknown)
        == keys(inadequate)
        == {("cameras", "camera-scope"), ("networks", "dvr-uplink-review")}
    )
    assert unknown.questions == ("Confirm whether the existing DVR uplink is adequate.",)
    assert inadequate.questions == ("Resolve the inadequate DVR uplink.",)
    assert unknown.proposed_lines == inadequate.proposed_lines == ()


def test_inferred_uplink_is_not_verified_support() -> None:
    inferred = Fact(True, Certainty.INFERRED)
    result = route_specialties(
        RoutingRequest(
            "p", CameraScope("analog_coax", confirmed(2), existing_uplink_adequate=inferred)
        )
    )
    assert ("networks", "dvr-uplink-review") in keys(result)
    assert result.questions == ("Confirm whether the existing DVR uplink is adequate.",)


def test_known_switch_facts_still_require_network_review() -> None:
    result = route_specialties(
        RoutingRequest(
            "p",
            CameraScope(
                "poe_ethernet", confirmed(4), confirmed("SW-1"), confirmed(100.0), confirmed(8)
            ),
            explicit_specialties=("cameras", "networks"),
        )
    )
    assert keys(result) == {("cameras", "camera-scope"), ("networks", "poe-uplink")}
    assert result.proposed_lines == ()


def test_route_change_is_local_and_mixed_project_history_is_rejected() -> None:
    routes = (
        RacewayScope("east", False, confirmed(10.0), confirmed(True), confirmed(4.0)),
        RacewayScope("west", False, confirmed(12.0), confirmed(True), confirmed(5.0)),
    )
    before = RoutingRequest("p", CameraScope("analog_coax", confirmed(2)), routes)
    changed = route_specialties(
        replace(
            before, raceways=(replace(routes[0], capacity_verified=confirmed(False)), routes[1])
        ),
        previous=before,
    )
    assert changed.invalidated_evidence == ("raceway:east:capacity",)
    assert "Confirm raceway capacity for east." in changed.questions
    assert all("west" not in question for question in changed.questions)
    with pytest.raises(ValueError, match="another project"):
        route_specialties(replace(before, project_id="other"), previous=before)


def test_switch_edit_invalidates_network_evidence() -> None:
    before_camera = CameraScope(
        "poe_ethernet", confirmed(4), confirmed("SW-1"), confirmed(100.0), confirmed(8)
    )
    before = RoutingRequest("p", before_camera, (RacewayScope("other"),))
    changes = (
        replace(before_camera, existing_switch_model=confirmed("SW-2")),
        replace(before_camera, existing_switch_poe_w=confirmed(120.0)),
        replace(before_camera, existing_switch_free_ports=confirmed(7)),
    )
    for changed_camera in changes:
        result = route_specialties(replace(before, cameras=changed_camera), previous=before)
        assert result.invalidated_evidence == ("network:poe-link", "network:switch")
        assert all("raceway" not in item for item in result.invalidated_evidence)


def test_removed_camera_invalidates_only_its_linked_route() -> None:
    before = RoutingRequest(
        "p",
        CameraScope("poe_ethernet", confirmed(4)),
        (RacewayScope("camera", linked_to_camera=True), RacewayScope("other")),
    )
    result = route_specialties(replace(before, cameras=None), previous=before)
    assert result.invalidated_evidence == (
        "camera:count",
        "camera:scope",
        "network:poe-link",
        "raceway:camera:link",
    )
    assert keys(result) == {("raceway", "camera"), ("raceway", "other")}
    assert result.proposed_lines == ()


def test_route_linkage_change_and_route_removal_stale_only_that_link() -> None:
    routes = (RacewayScope("camera", linked_to_camera=True), RacewayScope("other"))
    before = RoutingRequest("p", CameraScope("poe_ethernet", confirmed(4)), routes)
    unlinked = replace(before, raceways=(replace(routes[0], linked_to_camera=False), routes[1]))
    assert route_specialties(unlinked, previous=before).invalidated_evidence == (
        "raceway:camera:link",
    )
    assert route_specialties(before, previous=unlinked).invalidated_evidence == (
        "raceway:camera:link",
    )
    removed = replace(before, raceways=(routes[1],))
    assert route_specialties(removed, previous=before).invalidated_evidence == (
        "raceway:camera:link",
        "raceway:camera:route",
    )
