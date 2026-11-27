"""Disabled-by-default local scope preview boundary; no provider is installed."""

import os
from typing import Annotated, Literal, Protocol
from uuid import UUID

import psycopg
from fastapi import Depends, Header, HTTPException, status
from psycopg.types.json import Jsonb
from pydantic import BaseModel, ConfigDict, Field, field_validator

from estimate_api.authorization import get_interactive_actor
from estimate_api.projects import (
    ProjectRepository,
    ProjectView,
    get_repository,
    require_project_access,
)


class PreviewRequest(BaseModel):
    brief: str = Field(min_length=1, max_length=4000)

    @field_validator("brief")
    @classmethod
    def nonblank(cls, brief: str) -> str:
        if not brief.strip():
            raise ValueError("brief is required")
        return brief


class PreviewProposal(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    status: Literal["insufficient_stock", "needs_review"]
    available_quantity: int | None = Field(default=None, alias="availableQuantity", ge=0)


class PreviewDraft(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    requested_quantity: int = Field(alias="requestedQuantity", ge=1)
    question: str = Field(min_length=1)
    evidence_ids: list[str] = Field(alias="evidenceIds")
    proposal: PreviewProposal


class PreviewResponse(PreviewDraft):
    project_id: UUID = Field(alias="projectId")
    schema_version: Literal["scope-review-preview.v1"] = Field(
        default="scope-review-preview.v1", alias="schemaVersion"
    )
    state: Literal["pending_review"] = "pending_review"
    review_required: Literal[True] = Field(default=True, alias="reviewRequired")
    persisted: Literal[False] = False
    commercial_ready: Literal[False] = Field(default=False, alias="commercialReady")


class PreviewExtractor(Protocol):
    def extract(self, brief: str) -> PreviewDraft: ...


def get_preview_extractor() -> PreviewExtractor:
    # Product code never constructs an ADK or provider client implicitly.
    raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Preview unavailable")


class PreviewStore:
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    def reserve(self, actor: UUID, project_id: UUID, command_key: str) -> PreviewResponse | None:
        with psycopg.connect(self.dsn, autocommit=True, connect_timeout=3) as conn:
            with conn.transaction():
                conn.execute("set local statement_timeout = '3s'")
                login = conn.execute(
                    "select rolsuper, rolbypassrls, rolinherit, rolcanlogin "
                    "from pg_roles where rolname = session_user"
                ).fetchone()
                if login is None or login != (False, False, False, True):
                    raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Preview unavailable")
                # A single cross-process lock serializes all quota decisions.
                conn.execute("select pg_advisory_xact_lock(209, 1)")
                conn.execute("set local role authenticated")
                conn.execute("select set_config('request.jwt.claim.sub', %s, true)", (str(actor),))
                role = conn.execute(
                    "select case when p.owner_user_id = %s then 'owner' else m.role end "
                    "from public.projects p left join public.project_memberships m "
                    "on m.project_id = p.id and m.user_id = %s "
                    "where p.id = %s and (p.owner_user_id = %s or m.user_id is not null)",
                    (actor, actor, project_id, actor),
                ).fetchone()
                if role is None:
                    raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
                if role[0] not in ("owner", "editor"):
                    raise HTTPException(status.HTTP_403_FORBIDDEN, "Project editor required")
                conn.execute("set local role none")
                receipt = conn.execute(
                    "select state, response_json from private.preview_reservations "
                    "where actor_id = %s and project_id = %s and command_key = %s",
                    (actor, project_id, command_key),
                ).fetchone()
                if receipt and receipt[0] == "complete":
                    return PreviewResponse.model_validate(receipt[1])
                if receipt:
                    raise HTTPException(status.HTTP_409_CONFLICT, "Preview already reserved")
                counts = conn.execute(
                    "select count(*) filter (where actor_id = %s), "
                    "count(*) filter (where project_id = %s), count(*) "
                    "from private.preview_reservations "
                    "where created_at > clock_timestamp() - interval '1 hour'",
                    (actor, project_id),
                ).fetchone()
                if counts is None or counts[0] >= 2 or counts[1] >= 4 or counts[2] >= 8:
                    raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Preview quota reached")
                conn.execute(
                    "insert into private.preview_reservations"
                    "(actor_id, project_id, command_key, created_at) "
                    "values (%s, %s, %s, clock_timestamp())",
                    (actor, project_id, command_key),
                )
        return None

    def finish(
        self, actor: UUID, project_id: UUID, command_key: str, response: PreviewResponse | None
    ) -> None:
        with psycopg.connect(self.dsn, autocommit=True, connect_timeout=3) as conn:
            with conn.transaction():
                conn.execute("set local statement_timeout = '3s'")
                updated = conn.execute(
                    "update private.preview_reservations "
                    "set state = %s, response_json = %s "
                    "where actor_id = %s and project_id = %s and command_key = %s "
                    "and state = 'pending'",
                    (
                        "complete" if response else "failed",
                        (
                            Jsonb(response.model_dump(by_alias=True, mode="json"))
                            if response
                            else None
                        ),
                        actor,
                        project_id,
                        command_key,
                    ),
                )
                if updated.rowcount != 1:
                    raise RuntimeError("Preview receipt unavailable")


def get_preview_store() -> PreviewStore:
    if os.environ.get("ESTIMATE_PREVIEW_LOCAL_ENABLED") != "1":
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Preview unavailable")
    dsn = os.environ.get("ESTIMATE_PREVIEW_LOCAL_DSN")
    if not dsn:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Preview unavailable")
    return PreviewStore(dsn)


def require_preview_project(
    projectId: UUID,
    actor: Annotated[UUID, Depends(get_interactive_actor)],
    repository: Annotated[ProjectRepository, Depends(get_repository)],
) -> ProjectView:
    return require_project_access(projectId, actor, repository)


def preview_scope_review(
    projectId: UUID,
    request: PreviewRequest,
    project: Annotated[ProjectView, Depends(require_preview_project)],
    actor: Annotated[UUID, Depends(get_interactive_actor)],
    store: Annotated[PreviewStore, Depends(get_preview_store)],
    extractor: Annotated[PreviewExtractor, Depends(get_preview_extractor)],
    command_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=100)],
) -> PreviewResponse:
    if project.id != projectId:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    try:
        prior = store.reserve(actor, projectId, command_key)
    except psycopg.Error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Preview unavailable") from None
    if prior is not None:
        return prior
    try:
        draft = extractor.extract(request.brief)
        response = PreviewResponse(projectId=projectId, **draft.model_dump(by_alias=True))
    except Exception:
        try:
            store.finish(actor, projectId, command_key, None)
        except (psycopg.Error, RuntimeError):
            pass  # The pending receipt still blocks a second extractor call.
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Preview unavailable") from None
    try:
        store.finish(actor, projectId, command_key, response)
    except (psycopg.Error, RuntimeError):
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Preview unavailable") from None
    return response
