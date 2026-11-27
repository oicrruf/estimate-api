"""Local-only projection of the synthetic ADK/Relate camera proof to the API DTO."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from demo.agent.private_camera import CameraExtractor, run_camera
from estimate_api.preview import PreviewDraft, PreviewProposal

REVIEW_QUESTION = "Confirm camera quantity and shared stock before any quotation."
REQUIRED_EVIDENCE = {"EV-CAM-POE", "EV-POOL-CAM"}


@dataclass(frozen=True)
class LocalCameraPreviewAdapter:
    store_path: Path
    extractor: CameraExtractor

    def extract(self, brief: str) -> PreviewDraft:
        """Called by the synchronous FastAPI route after its auth and quota gate."""
        result = asyncio.run(run_camera(self.store_path, brief, self.extractor))
        if (
            result.get("mode") != "private-camera-intake.v1"
            or result.get("status") != "PENDING_REVIEW"
            or result.get("toolCalls") != 1
        ):
            raise ValueError("Synthetic camera review is incomplete")
        quantity = result.get("requestedQuantity")
        evaluation = result.get("evaluation")
        evidence_ids = result.get("evidenceIds")
        if (
            type(quantity) is not int
            or quantity not in (2, 4)
            or not isinstance(evaluation, dict)
            or not isinstance(evidence_ids, list)
            or not all(isinstance(item, str) for item in evidence_ids)
            or set(evidence_ids) != REQUIRED_EVIDENCE
        ):
            raise ValueError("Synthetic camera evidence is incomplete")
        candidates = evaluation.get("candidates")
        available = evaluation.get("availableQuantity")
        if (
            evaluation.get("scenario") != "camera"
            or evaluation.get("requestedQuantity") != quantity
            or type(available) is not int
            or available != 2
            or not isinstance(candidates, list)
            or len(candidates) != 1
            or not isinstance(candidates[0], dict)
        ):
            raise ValueError("Synthetic stock evaluation is incomplete")
        candidate: dict[str, Any] = candidates[0]
        if candidate.get("productId") != "CAM-POE":
            raise ValueError("Unexpected synthetic product")
        stock_status = candidate.get("status")
        proposal_status: Literal["insufficient_stock", "needs_review"]
        if (
            stock_status == "INSUFFICIENT_STOCK"
            and available < quantity
            and candidate.get("reasonCodes") == ["SHARED_POOL_CAPACITY"]
            and evaluation.get("selectedProductId") is None
        ):
            proposal_status = "insufficient_stock"
        elif (
            stock_status == "COMPATIBLE"
            and available >= quantity
            and candidate.get("reasonCodes") == ["MEETS_REQUIREMENTS"]
            and evaluation.get("selectedProductId") == "CAM-POE"
        ):
            proposal_status = "needs_review"
        else:
            raise ValueError("Synthetic stock status is inconsistent")
        # Never expose offer IDs, fictitious prices, model text or usage metrics.
        return PreviewDraft(
            requestedQuantity=quantity,
            question=REVIEW_QUESTION,
            evidenceIds=sorted(evidence_ids),
            proposal=PreviewProposal(status=proposal_status, availableQuantity=available),
        )
