"""Pure scope-to-specialist handoff with synthetic admitted evidence."""

from dataclasses import replace

import pytest

from estimate_api.chat.specialty_handoff import LocalEvidenceBinding, preview_specialist_handoff
from estimate_api.domain.scope_capture import Certainty, Fact, ScopeIntake
from estimate_api.domain.scope_capture.contract import (
    AssetAvailability,
    AssetValidation,
    ClientAsset,
    SupplyItem,
    SupplyOwner,
)
from estimate_api.specialties.routing import CameraScope, RacewayScope, RoutingRequest


def confirmed[T](value: T, evidence: str) -> Fact[T]:
    return Fact(value, Certainty.CONFIRMED, evidence)


SCOPE = ScopeIntake("Synthetic camera site")


def binding(
    evidence_id: str, field: str, value: object, *, project: str = "site-1", revision: int = 1
) -> LocalEvidenceBinding:
    return LocalEvidenceBinding(evidence_id, project, field, value, revision)


COUNT_1 = binding("count-1", "camera.count", 4)


def test_poe_unknown_switch_passes_questions_and_evidence_reasons() -> None:
    request = RoutingRequest("site-1", CameraScope("poe_ethernet", confirmed(4, "count-1")))
    result = preview_specialist_handoff(
        SCOPE, request, evidence_bindings=(COUNT_1,), evidence_revision=1
    )
    assert result.persisted is False
    assert {a.specialty for a in result.routing.assignments} == {"cameras", "networks"}
    assert "Confirm the existing switch model." in result.routing.questions
    assert "Confirm the existing switch PoE power budget." in result.routing.questions
    assert "network:switch" in result.evidence_reasons
    assert result.routing.proposed_lines == ()


def test_analog_dvr_confirmed_uplink_reuses_existing_asset() -> None:
    request = RoutingRequest(
        "site-1",
        CameraScope(
            "analog_coax",
            confirmed(4, "count-1"),
            existing_uplink_adequate=confirmed(True, "uplink-1"),
        ),
    )
    result = preview_specialist_handoff(
        SCOPE,
        request,
        evidence_bindings=(COUNT_1, binding("uplink-1", "camera.existing_uplink_adequate", True)),
        evidence_revision=1,
    )
    assert [(a.specialty, a.key) for a in result.routing.assignments] == [
        ("cameras", "camera-scope")
    ]
    assert result.routing.questions == ()
    assert result.routing.proposed_lines == ()


def test_wifi_unknown_capacity_stays_pending_without_poe_link() -> None:
    request = RoutingRequest("site-1", CameraScope("wifi", confirmed(3, "count-1")))
    result = preview_specialist_handoff(
        SCOPE,
        request,
        evidence_bindings=(binding("count-1", "camera.count", 3),),
        evidence_revision=1,
    )
    assert [(a.specialty, a.key) for a in result.routing.assignments] == [
        ("cameras", "camera-scope"),
        ("networks", "wifi-capacity-review"),
    ]
    assert result.routing.questions == ("Confirm existing Wi-Fi capacity with evidence.",)
    assert "network:wifi-capacity" in result.evidence_reasons
    assert "network:poe-link" not in result.evidence_reasons


def test_unadmitted_confirmation_rejected_and_inference_remains_question() -> None:
    request = RoutingRequest("site-1", CameraScope("wifi", confirmed(3, "llm-claim")))
    with pytest.raises(ValueError, match="matching local evidence"):
        preview_specialist_handoff(SCOPE, request, evidence_bindings=(), evidence_revision=1)
    inferred = Fact(True, Certainty.INFERRED)
    request = replace(
        request,
        cameras=CameraScope(
            "wifi", confirmed(3, "count-1"), existing_wifi_capacity_verified=inferred
        ),
    )
    result = preview_specialist_handoff(
        SCOPE,
        request,
        evidence_bindings=(binding("count-1", "camera.count", 3),),
        evidence_revision=1,
    )
    assert result.routing.questions == ("Confirm existing Wi-Fi capacity with evidence.",)


def test_count_edit_invalidates_only_explicitly_linked_route() -> None:
    before = RoutingRequest(
        "site-1",
        CameraScope("wifi", confirmed(3, "count-1")),
        (RacewayScope("camera", linked_to_camera=True), RacewayScope("unrelated")),
    )
    after = replace(before, cameras=CameraScope("wifi", confirmed(4, "count-2")))
    result = preview_specialist_handoff(
        SCOPE,
        after,
        evidence_bindings=(binding("count-2", "camera.count", 4),),
        evidence_revision=1,
        previous=before,
    )
    assert result.routing.invalidated_evidence == ("camera:count", "raceway:camera:link")
    assert all("unrelated" not in reason for reason in result.routing.invalidated_evidence)


@pytest.mark.parametrize(
    "wrong_binding",
    [
        binding("count-1", "camera.count", 5),
        binding("count-1", "camera.count", 4, project="other"),
        binding("count-1", "camera.count", 4, revision=0),
        binding("count-1", "camera.existing_switch_free_ports", 4),
    ],
)
def test_mismatched_value_project_revision_or_specialty_field_rejected(
    wrong_binding: LocalEvidenceBinding,
) -> None:
    request = RoutingRequest("site-1", CameraScope("poe_ethernet", confirmed(4, "count-1")))
    with pytest.raises(ValueError, match="matching local evidence"):
        preview_specialist_handoff(
            SCOPE, request, evidence_bindings=(wrong_binding,), evidence_revision=1
        )


def test_same_id_cannot_certify_two_incompatible_fields() -> None:
    request = RoutingRequest(
        "site-1",
        CameraScope(
            "analog_coax",
            confirmed(4, "shared"),
            existing_uplink_adequate=confirmed(True, "shared"),
        ),
    )
    with pytest.raises(ValueError, match="matching local evidence"):
        preview_specialist_handoff(
            SCOPE,
            request,
            evidence_bindings=(binding("shared", "camera.count", 4),),
            evidence_revision=1,
        )


@pytest.mark.parametrize(
    "scope",
    [
        replace(
            SCOPE,
            client_assets=(
                ClientAsset(
                    "switch", AssetAvailability.AVAILABLE, AssetValidation.VALIDATED, "local-claim"
                ),
            ),
        ),
        replace(SCOPE, client_assets_absence_evidence="local-claim"),
        replace(SCOPE, supplies_absence_evidence="local-claim"),
        replace(SCOPE, supplies=(SupplyItem("switch", SupplyOwner.CONTRACTOR, True),)),
    ],
)
def test_unsupported_scope_assertions_fail_closed(scope: ScopeIntake) -> None:
    request = RoutingRequest("site-1", CameraScope("wifi", confirmed(3, "count-1")))
    with pytest.raises(ValueError, match="unsupported scope assertion"):
        preview_specialist_handoff(
            scope,
            request,
            evidence_bindings=(binding("count-1", "camera.count", 3),),
            evidence_revision=1,
        )


@pytest.mark.parametrize("revision", [True, 1.0, -1])
def test_non_integer_or_negative_evidence_revision_rejected(revision: object) -> None:
    request = RoutingRequest("site-1", CameraScope("wifi", confirmed(3, "count-1")))
    with pytest.raises(ValueError, match="revision"):
        preview_specialist_handoff(
            SCOPE,
            request,
            evidence_bindings=(binding("count-1", "camera.count", 3),),
            evidence_revision=revision,  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="revisions"):
        preview_specialist_handoff(
            SCOPE,
            request,
            evidence_bindings=(
                binding("count-1", "camera.count", 3, revision=revision),  # type: ignore[arg-type]
            ),
            evidence_revision=1,
        )
