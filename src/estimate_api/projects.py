"""Project reads with PostgreSQL RLS and transaction-scoped identity."""

import os
from functools import lru_cache
from typing import Annotated, Literal
from uuid import UUID

import psycopg
from fastapi import Depends, HTTPException, status
from psycopg.rows import dict_row
from pydantic import BaseModel

from estimate_api.authorization import get_interactive_actor


class ProjectView(BaseModel):
    id: UUID
    name: str
    revision: int
    access_role: Literal["owner", "editor", "viewer"]


class ProjectPage(BaseModel):
    items: list[ProjectView]
    next_cursor: UUID | None


class UnsafeReadRole(Exception):
    """The configured database login is too privileged for RLS reads."""


_READ_SQL = """
select p.id, p.name, p.revision,
       case when p.owner_user_id = %(actor)s then 'owner' else m.role end as access_role
from public.projects p
left join public.project_memberships m
  on m.project_id = p.id and m.user_id = %(actor)s
where (p.owner_user_id = %(actor)s or m.user_id is not null)
"""


class ProjectRepository:
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    def read(
        self,
        actor: UUID,
        project_id: UUID | None = None,
        *,
        limit: int | None = None,
        cursor: UUID | None = None,
    ) -> list[ProjectView]:
        # A new connection is used for this initial cut; any later pool must
        # preserve the same transaction boundary and reset guarantees.
        with psycopg.connect(
            self.dsn, autocommit=True, connect_timeout=3, row_factory=dict_row
        ) as conn:
            with conn.transaction():
                conn.execute("set transaction read only isolation level read committed")
                login = conn.execute(
                    "select rolsuper, rolbypassrls, rolinherit, rolcanlogin "
                    "from pg_roles where rolname = session_user"
                ).fetchone()
                if (
                    login is None
                    or login["rolsuper"]
                    or login["rolbypassrls"]
                    or login["rolinherit"]
                    or not login["rolcanlogin"]
                ):
                    raise UnsafeReadRole
                conn.execute("set local role authenticated")
                conn.execute("select set_config('request.jwt.claim.sub', %s, true)", (str(actor),))
                sql = _READ_SQL
                params: dict[str, UUID | int] = {"actor": actor}
                if project_id is not None:
                    sql += " and p.id = %(project_id)s"
                    params["project_id"] = project_id
                if cursor is not None:
                    sql += " and p.id > %(cursor)s"
                    params["cursor"] = cursor
                sql += " order by p.id"
                if limit is not None:
                    sql += " limit %(limit)s"
                    params["limit"] = limit
                rows = conn.execute(sql, params).fetchall()
                return [ProjectView.model_validate(row) for row in rows]


@lru_cache(maxsize=1)
def get_repository() -> ProjectRepository:
    dsn = os.environ.get("ESTIMATE_DB_READ_DSN")
    if not dsn:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Project storage unavailable")
    return ProjectRepository(dsn)


def require_project_access(
    project_id: UUID,
    actor: Annotated[UUID, Depends(get_interactive_actor)],
    repository: Annotated[ProjectRepository, Depends(get_repository)],
) -> ProjectView:
    """Resolve an admitted actor's current project role through AT-208 RLS.

    This is a request gate. A mutable operation must recheck membership in
    its own trusted transaction before it charges or commits.
    """
    try:
        projects = repository.read(actor, project_id)
    except (psycopg.Error, UnsafeReadRole):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Project storage unavailable"
        ) from None
    if not projects:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    return projects[0]
