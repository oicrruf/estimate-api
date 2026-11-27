"""Small synthetic projection regressions; no provider or HTTP fixture."""

from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("google.adk")

from demo.agent.graph import seed_store
from demo.agent.scope_preview_adapter import LocalCameraPreviewAdapter
from demo.private_model import MAX_DESCRIPTION_CHARS


class FakeCameraModel:
    model = "synthetic-test-only"

    def __init__(self, quantity: int | None) -> None:
        self.quantity = quantity
        self.calls = 0

    async def extract(self, description: str) -> tuple[dict[str, Any], dict[str, int]]:
        self.calls += 1
        return {"requested_quantity": self.quantity}, {"syntheticCalls": 1}


@pytest.mark.parametrize(
    ("description", "quantity", "status"),
    [
        ("Four cameras for a synthetic fixture.", 4, "insufficient_stock"),
        ("Two cameras for a synthetic fixture.", 2, "needs_review"),
    ],
)
def test_adapter_projects_only_pending_review(
    tmp_path: Path, description: str, quantity: int, status: str
) -> None:
    store = tmp_path / "synthetic.rl"
    seed_store(store)
    model = FakeCameraModel(quantity)
    result = LocalCameraPreviewAdapter(store, model).extract(description)
    assert model.calls == 1
    assert result.model_dump(by_alias=True) == {
        "requestedQuantity": quantity,
        "question": "Confirm camera quantity and shared stock before any quotation.",
        "evidenceIds": ["EV-CAM-POE", "EV-POOL-CAM"],
        "proposal": {"status": status, "availableQuantity": 2},
    }


def test_adapter_rejects_ambiguity_without_graph(tmp_path: Path) -> None:
    model = FakeCameraModel(None)
    with pytest.raises(ValueError, match="incomplete"):
        LocalCameraPreviewAdapter(tmp_path / "unused.rl", model).extract(
            "Perhaps two or four cameras in a synthetic fixture."
        )
    assert model.calls == 1


def test_adapter_rejects_overlong_input_before_model(tmp_path: Path) -> None:
    model = FakeCameraModel(4)
    with pytest.raises(ValueError, match="700"):
        LocalCameraPreviewAdapter(tmp_path / "unused.rl", model).extract(
            "x" * (MAX_DESCRIPTION_CHARS + 1)
        )
    assert model.calls == 0
