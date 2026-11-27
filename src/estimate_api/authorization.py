"""Interactive admission after Supabase has authenticated the user."""

import json
import os
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status

from estimate_api.auth import get_actor


def _allowed_subjects() -> set[UUID]:
    """Read the backend-managed demo allowlist; absence denies every actor."""
    configured = os.environ.get("ESTIMATE_INTERACTIVE_ALLOWED_SUBJECTS", "[]")
    try:
        values = json.loads(configured)
        if not isinstance(values, list) or len(values) > 1000:
            raise ValueError
        if not all(isinstance(value, str) for value in values):
            raise ValueError
        return {UUID(value) for value in values}
    except (ValueError, TypeError, json.JSONDecodeError):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Interactive authorization unavailable"
        ) from None


def get_interactive_actor(actor: Annotated[UUID, Depends(get_actor)]) -> UUID:
    """A signed token establishes identity; explicit admission grants app use."""
    if actor not in _allowed_subjects():
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Interactive access denied")
    return actor
