"""Test-only FastAPI entry point with a synthetic extractor override."""

from uuid import UUID

import psycopg

from estimate_api.app import app
from estimate_api.preview import (
    PreviewDraft,
    PreviewProposal,
    PreviewResponse,
    PreviewStore,
    get_preview_extractor,
    get_preview_store,
)

calls = 0


class SyntheticExtractor:
    def extract(self, brief: str) -> PreviewDraft:
        global calls
        calls += 1
        if brief == "synthetic-stub-error":
            raise RuntimeError("Synthetic extractor failure")
        return PreviewDraft(
            requestedQuantity=4,
            question="Confirme disponibilidad antes de cotizar.",
            evidenceIds=["EV-POOL-CAM"],
            proposal=PreviewProposal(status="insufficient_stock", availableQuantity=2),
        )


app.dependency_overrides[get_preview_extractor] = SyntheticExtractor


class SyntheticStore(PreviewStore):
    def finish(
        self, actor: UUID, project_id: UUID, command_key: str, response: PreviewResponse | None
    ) -> None:
        if command_key == "synthetic-finish-error":
            raise psycopg.OperationalError("synthetic receipt failure")
        super().finish(actor, project_id, command_key, response)


def get_synthetic_store() -> SyntheticStore:
    return SyntheticStore(get_preview_store().dsn, max_brief_chars=700)


app.dependency_overrides[get_preview_store] = get_synthetic_store


@app.get("/_test/extractor-count", include_in_schema=False)
def count_extractions() -> dict[str, int]:
    return {"calls": calls}
