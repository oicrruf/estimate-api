"""Minimal application boundary. Future services attach in their own issues."""

from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


app = FastAPI(
    title="Estimate Agent API",
    version="0.1.0",
    description="Versioned bootstrap contract for Estimate Agent.",
)


@app.get("/health", operation_id="health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    """Report that the API process is responding."""
    return HealthResponse()
