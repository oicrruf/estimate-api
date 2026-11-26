"""Minimal application boundary. Future services attach in their own issues."""

from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from estimate_api.chat.preview import router as chat_router


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


app = FastAPI(
    title="Estimate Agent API",
    version="0.1.0",
    openapi_version="3.1.0",
    description="Versioned bootstrap contract for Estimate Agent.",
)
app.include_router(chat_router)


@app.get("/health", operation_id="health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    """Report that the API process is responding."""
    return HealthResponse()
