"""Minimal application boundary. Future services attach in their own issues."""

from typing import Annotated, Literal
from uuid import UUID

import psycopg
from fastapi import Depends, FastAPI, HTTPException, Query, status
from pydantic import BaseModel

from estimate_api.authorization import get_interactive_actor
from estimate_api.chat.preview import router as chat_router
from estimate_api.preview import PreviewResponse, preview_scope_review
from estimate_api.projects import (
    ProjectPage,
    ProjectRepository,
    ProjectView,
    UnsafeReadRole,
    get_repository,
    require_project_access,
)


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


@app.get(
    "/projects",
    operation_id="listProjects",
    response_model=ProjectPage,
    responses={
        401: {"description": "Invalid or missing Bearer token"},
        403: {"description": "Interactive access denied"},
        503: {"description": "Authentication or storage unavailable"},
    },
    tags=["projects"],
)
def list_projects(
    actor: Annotated[UUID, Depends(get_interactive_actor)],
    repository: Annotated[ProjectRepository, Depends(get_repository)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: UUID | None = None,
) -> ProjectPage:
    try:
        rows = repository.read(actor, limit=limit + 1, cursor=cursor)
    except (psycopg.Error, UnsafeReadRole):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Project storage unavailable"
        ) from None
    return ProjectPage(
        items=rows[:limit], next_cursor=rows[limit - 1].id if len(rows) > limit else None
    )


@app.get(
    "/projects/{project_id}",
    operation_id="getProject",
    response_model=ProjectView,
    responses={
        401: {"description": "Invalid or missing Bearer token"},
        403: {"description": "Interactive access denied"},
        404: {"description": "Project not found"},
        503: {"description": "Authentication or storage unavailable"},
    },
    tags=["projects"],
)
def get_project(
    project: Annotated[ProjectView, Depends(require_project_access)],
) -> ProjectView:
    return project


app.add_api_route(
    "/v1/projects/{projectId}/scope-review-preview",
    preview_scope_review,
    methods=["POST"],
    operation_id="previewScopeReviewV1",
    response_model=PreviewResponse,
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Actor is not admitted or cannot edit this project"},
        404: {"description": "Project not found"},
        409: {"description": "Preview already reserved"},
        429: {"description": "Preview quota reached"},
        503: {"description": "Preview unavailable"},
    },
    tags=["projects"],
)
