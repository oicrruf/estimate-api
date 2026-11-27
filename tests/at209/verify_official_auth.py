"""Exercise the actual HTTP boundary with official disposable GoTrue JWTs."""

import json
import os
import secrets
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID

import psycopg
from fastapi.testclient import TestClient

from estimate_api.app import app
from estimate_api.auth import get_verifier
from estimate_api.projects import get_repository

ISSUER = "http://127.0.0.1:55424"


def signup(email: str) -> tuple[UUID, str]:
    request = urllib.request.Request(
        ISSUER + "/signup",
        data=json.dumps({"email": email, "password": secrets.token_urlsafe(24)}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        body = json.load(response)
    return UUID(body["user"]["id"]), body["access_token"]


def uvicorn_smoke(
    owner_token: str,
    member_token: str,
    unadmitted_token: str,
    owner: UUID,
    member: UUID,
    project: UUID,
    extras: tuple[tuple[UUID, str], tuple[UUID, str], tuple[UUID, str]],
    second_project: UUID,
    third_project: UUID,
) -> None:
    """Check the same FastAPI routes over a real loopback HTTP socket."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    server = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "tests.at209.preview_server:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(base + "/health", timeout=1) as response:
                    if response.status == 200:
                        break
            except (urllib.error.URLError, TimeoutError):
                time.sleep(0.1)
        else:
            raise AssertionError("Disposable FastAPI server did not start")
        try:
            urllib.request.urlopen(base + "/projects", timeout=3)
        except urllib.error.HTTPError as error:
            assert error.code == 401
        else:
            raise AssertionError("Missing Bearer token was accepted")
        request = urllib.request.Request(
            base + f"/projects/{project}",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        with urllib.request.urlopen(request, timeout=3) as response:
            assert response.status == 200
            assert json.load(response)["id"] == str(project)

        def preview(
            token: str | None,
            key: str,
            target_project: UUID = project,
            brief: str = "Cuatro cámaras PoE sintéticas",
        ) -> tuple[int, dict[str, object]]:
            headers = {"Content-Type": "application/json", "Idempotency-Key": key}
            if token is not None:
                headers["Authorization"] = f"Bearer {token}"
            request = urllib.request.Request(
                base + f"/v1/projects/{target_project}/scope-review-preview",
                data=json.dumps({"brief": brief}).encode(),
                headers=headers,
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=5) as response:
                    return response.status, json.load(response)
            except urllib.error.HTTPError as error:
                return error.code, json.load(error)

        def calls() -> int:
            with urllib.request.urlopen(base + "/_test/extractor-count", timeout=3) as response:
                return int(json.load(response)["calls"])

        assert preview(None, "missing-token")[0] == 401
        assert preview("invalid-synthetic-token", "invalid-token")[0] == 401
        assert preview(unadmitted_token, "not-admitted")[0] == 403
        assert preview(member_token, "no-membership")[0] == 404
        assert preview(owner_token, "blank", brief="   ")[0] == 422
        assert preview(owner_token, "too-long", brief="x" * 4001)[0] == 422
        assert calls() == 0
        with psycopg.connect(os.environ["ESTIMATE_DB_TEST_ADMIN_DSN"]) as conn:
            assert conn.execute("select count(*) from private.preview_reservations").fetchone() == (
                0,
            )

        # Hold the quota lock while a real HTTP request passes the early project
        # read; a second connection changes membership before reserve reads it.
        with psycopg.connect(os.environ["ESTIMATE_DB_TEST_ADMIN_DSN"], autocommit=True) as conn:
            conn.execute("select set_config('request.jwt.claim.sub', %s, false)", (str(owner),))
            conn.execute(
                "insert into public.project_memberships(project_id,user_id,role) "
                "values (%s,%s,'editor')",
                (project, member),
            )

        def denied_after_change(change_sql: str, expected: int, key: str) -> None:
            with (
                psycopg.connect(
                    os.environ["ESTIMATE_DB_TEST_ADMIN_DSN"], autocommit=True
                ) as blocker,
                ThreadPoolExecutor(max_workers=1) as executor,
            ):
                blocker.execute("select pg_advisory_lock(209, 1)")
                future = executor.submit(preview, member_token, key)
                try:
                    deadline = time.monotonic() + 4
                    while time.monotonic() < deadline:
                        waiting = blocker.execute(
                            "select count(*) from pg_locks "
                            "where locktype = 'advisory' and not granted"
                        ).fetchone()
                        if waiting and waiting[0] >= 1:
                            break
                        time.sleep(0.02)
                    else:
                        raise AssertionError("HTTP reserve did not reach the quota lock")
                    with psycopg.connect(
                        os.environ["ESTIMATE_DB_TEST_ADMIN_DSN"], autocommit=True
                    ) as changer:
                        changer.execute(
                            "select set_config('request.jwt.claim.sub', %s, false)",
                            (str(owner),),
                        )
                        changer.execute(change_sql, (project, member))
                finally:
                    blocker.execute("select pg_advisory_unlock(209, 1)")
                assert future.result(timeout=5)[0] == expected
            assert calls() == 0
            with psycopg.connect(os.environ["ESTIMATE_DB_TEST_ADMIN_DSN"]) as check:
                assert check.execute(
                    "select count(*) from private.preview_reservations"
                ).fetchone() == (0,)

        denied_after_change(
            "update public.project_memberships set role = 'viewer' "
            "where project_id = %s and user_id = %s",
            403,
            "degraded-before-reserve",
        )
        with psycopg.connect(os.environ["ESTIMATE_DB_TEST_ADMIN_DSN"], autocommit=True) as conn:
            conn.execute("select set_config('request.jwt.claim.sub', %s, false)", (str(owner),))
            conn.execute(
                "update public.project_memberships set role = 'editor' "
                "where project_id = %s and user_id = %s",
                (project, member),
            )
        denied_after_change(
            "delete from public.project_memberships where project_id = %s and user_id = %s",
            404,
            "revoked-before-reserve",
        )

        status_code, body = preview(owner_token, "first")
        assert status_code == 200
        assert body == {
            "schemaVersion": "scope-review-preview.v1",
            "projectId": str(project),
            "state": "pending_review",
            "requestedQuantity": 4,
            "question": "Confirme disponibilidad antes de cotizar.",
            "evidenceIds": ["EV-POOL-CAM"],
            "proposal": {"status": "insufficient_stock", "availableQuantity": 2},
            "reviewRequired": True,
            "persisted": False,
            "commercialReady": False,
        }
        assert preview(owner_token, "first") == (200, body)
        assert calls() == 1
        with psycopg.connect(os.environ["ESTIMATE_DB_TEST_ADMIN_DSN"]) as conn:
            assert conn.execute(
                "select count(*) from private.preview_reservations "
                "where actor_id = %s and project_id = %s",
                (owner, project),
            ).fetchone() == (1,)

        # One slot remains for this actor; concurrent requests cannot both reserve it.
        with ThreadPoolExecutor(max_workers=2) as executor:
            statuses = list(
                executor.map(lambda key: preview(owner_token, key)[0], ("race-a", "race-b"))
            )
        assert sorted(statuses) == [200, 429]
        assert calls() == 2
        with psycopg.connect(os.environ["ESTIMATE_DB_TEST_ADMIN_DSN"], autocommit=True) as conn:
            conn.execute("select set_config('request.jwt.claim.sub', %s, false)", (str(owner),))
            conn.execute(
                "insert into public.project_memberships(project_id,user_id,role) "
                "values (%s,%s,'viewer')",
                (project, member),
            )
        assert preview(member_token, "viewer-denied")[0] == 403
        with psycopg.connect(os.environ["ESTIMATE_DB_TEST_ADMIN_DSN"], autocommit=True) as conn:
            conn.execute("select set_config('request.jwt.claim.sub', %s, false)", (str(owner),))
            conn.execute(
                "update public.project_memberships set role = 'editor' "
                "where project_id = %s and user_id = %s",
                (project, member),
            )
            conn.execute(
                "insert into public.project_memberships(project_id,user_id,role) "
                "values (%s,%s,'editor')",
                (project, extras[0][0]),
            )
        assert preview(member_token, "member-1")[0] == 200
        assert preview(member_token, "member-2")[0] == 200
        assert preview(extras[0][1], "project-limit")[0] == 429
        assert calls() == 4
        assert preview(extras[0][1], "second-1", second_project)[0] == 200
        assert preview(extras[0][1], "second-2", second_project)[0] == 200
        assert preview(extras[1][1], "second-3", second_project)[0] == 200
        assert preview(extras[1][1], "second-4", second_project)[0] == 200
        assert preview(extras[2][1], "global-limit", third_project)[0] == 429
        assert calls() == 8
        with psycopg.connect(os.environ["ESTIMATE_DB_TEST_ADMIN_DSN"]) as conn:
            assert conn.execute("select count(*) from private.preview_reservations").fetchone() == (
                8,
            )
            assert conn.execute(
                "select count(*) from private.preview_reservations "
                "where state = 'complete' and response_json is not null"
            ).fetchone() == (8,)
            conn.execute("delete from private.preview_reservations")
        assert (
            preview(extras[2][1], "stub-failure", third_project, "synthetic-stub-error")[0] == 503
        )
        assert calls() == 9
        assert preview(extras[2][1], "stub-failure", third_project)[0] == 409
        assert calls() == 9
        with psycopg.connect(os.environ["ESTIMATE_DB_TEST_ADMIN_DSN"]) as conn:
            assert conn.execute(
                "select state, response_json from private.preview_reservations "
                "where command_key = 'stub-failure'"
            ).fetchone() == ("failed", None)
            assert conn.execute("select count(*) from private.preview_reservations").fetchone() == (
                1,
            )
        assert preview(extras[2][1], "synthetic-finish-error", third_project)[0] == 503
        assert calls() == 10
        assert preview(extras[2][1], "synthetic-finish-error", third_project)[0] == 409
        assert calls() == 10
        assert preview(extras[2][1], "after-two-failures", third_project)[0] == 429
        assert calls() == 10
        with psycopg.connect(os.environ["ESTIMATE_DB_TEST_ADMIN_DSN"]) as conn:
            assert conn.execute(
                "select state, response_json from private.preview_reservations "
                "where command_key = 'synthetic-finish-error'"
            ).fetchone() == ("pending", None)
            assert conn.execute("select count(*) from private.preview_reservations").fetchone() == (
                2,
            )
            conn.execute("drop table private.preview_reservations")
        assert preview(extras[2][1], "db-failure", third_project)[0] == 503
        assert calls() == 10
    finally:
        server.terminate()
        server.wait(timeout=5)


def main() -> None:
    os.environ["ESTIMATE_SUPABASE_AUTH_ISSUER"] = ISSUER
    os.environ["ESTIMATE_SUPABASE_AUTH_AUDIENCE"] = "authenticated"
    get_verifier.cache_clear()
    get_repository.cache_clear()
    jwks = json.load(urllib.request.urlopen(ISSUER + "/.well-known/jwks.json", timeout=5))
    assert len(jwks["keys"]) == 1 and jwks["keys"][0]["kty"] == "EC"
    owner, owner_token = signup("at209-owner@example.invalid")
    member, member_token = signup("at209-member@example.invalid")
    _, unadmitted_token = signup("at209-unadmitted@example.invalid")
    extras = (
        signup("at209-extra-one@example.invalid"),
        signup("at209-extra-two@example.invalid"),
        signup("at209-extra-three@example.invalid"),
    )
    assert get_verifier().verify(owner_token) == owner
    assert get_verifier().verify(member_token) == member
    project = UUID("20000000-0000-0000-0000-000000000001")
    second_project = UUID("20000000-0000-0000-0000-000000000002")
    third_project = UUID("20000000-0000-0000-0000-000000000003")
    with psycopg.connect(os.environ["ESTIMATE_DB_TEST_ADMIN_DSN"], autocommit=True) as conn:
        conn.execute("select set_config('request.jwt.claim.sub', %s, false)", (str(owner),))
        conn.execute(
            "insert into public.projects(id, owner_user_id, name) values (%s, %s, %s)",
            (project, owner, "Proyecto Auth descartable"),
        )
        conn.execute("select set_config('request.jwt.claim.sub', %s, false)", (str(extras[0][0]),))
        conn.execute(
            "insert into public.projects(id, owner_user_id, name) values (%s, %s, %s)",
            (second_project, extras[0][0], "Segundo proyecto sintético"),
        )
        conn.execute("select set_config('request.jwt.claim.sub', %s, false)", (str(extras[2][0]),))
        conn.execute(
            "insert into public.projects(id, owner_user_id, name) values (%s, %s, %s)",
            (third_project, extras[2][0], "Tercer proyecto sintético"),
        )
        conn.execute(
            "insert into public.project_memberships(project_id,user_id,role) "
            "values (%s,%s,'editor')",
            (second_project, extras[1][0]),
        )
    with TestClient(app) as client:
        owner_headers = {"Authorization": f"Bearer {owner_token}"}
        member_headers = {"Authorization": f"Bearer {member_token}"}
        os.environ["ESTIMATE_INTERACTIVE_ALLOWED_SUBJECTS"] = json.dumps([str(owner)])
        assert client.get("/projects").status_code == 401
        assert (
            client.get(
                "/projects", headers={"Authorization": "Bearer invalid-synthetic-token"}
            ).status_code
            == 401
        )
        assert client.get("/projects", headers=owner_headers).json()["items"][0]["id"] == str(
            project
        )
        assert client.get(f"/projects/{project}", headers=owner_headers).status_code == 200
        assert client.get("/projects", headers=member_headers).status_code == 403
        os.environ["ESTIMATE_INTERACTIVE_ALLOWED_SUBJECTS"] = json.dumps([str(owner), str(member)])
        assert client.get("/projects", headers=member_headers).json()["items"] == []
        assert client.get(f"/projects/{project}", headers=member_headers).status_code == 404
        with psycopg.connect(os.environ["ESTIMATE_DB_TEST_ADMIN_DSN"], autocommit=True) as conn:
            conn.execute("select set_config('request.jwt.claim.sub', %s, false)", (str(owner),))
            conn.execute(
                "insert into public.project_memberships(project_id,user_id,role) "
                "values (%s,%s,'viewer')",
                (project, member),
            )
        assert (
            client.get("/projects", headers=member_headers).json()["items"][0]["access_role"]
            == "viewer"
        )
        assert (
            client.get("/projects", headers=owner_headers).json()["items"][0]["access_role"]
            == "owner"
        )
        with psycopg.connect(os.environ["ESTIMATE_DB_TEST_ADMIN_DSN"], autocommit=True) as conn:
            conn.execute("select set_config('request.jwt.claim.sub', %s, false)", (str(owner),))
            conn.execute(
                "delete from public.project_memberships where project_id=%s and user_id=%s",
                (project, member),
            )
        assert client.get("/projects", headers=member_headers).json()["items"] == []
        assert client.get(f"/projects/{project}", headers=member_headers).status_code == 404
        os.environ["ESTIMATE_PREVIEW_LOCAL_ENABLED"] = "0"
        assert (
            client.post(
                f"/v1/projects/{project}/scope-review-preview",
                json={"brief": "Prueba sintética"},
                headers={**owner_headers, "Idempotency-Key": "disabled-product"},
            ).status_code
            == 503
        )
        os.environ["ESTIMATE_PREVIEW_LOCAL_ENABLED"] = "1"
    os.environ["ESTIMATE_INTERACTIVE_ALLOWED_SUBJECTS"] = json.dumps(
        [str(owner), str(member), *(str(user) for user, _ in extras)]
    )
    uvicorn_smoke(
        owner_token,
        member_token,
        unadmitted_token,
        owner,
        member,
        project,
        extras,
        second_project,
        third_project,
    )
    print("Official disposable GoTrue -> FastAPI preview HTTP -> AT-208 RLS passed")


if __name__ == "__main__":
    main()
