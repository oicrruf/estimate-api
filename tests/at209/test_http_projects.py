"""Synthetic JWT and disposable PostgreSQL checks for the read-only HTTP cut."""

import json
import os
import threading
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from uuid import UUID

import jwt
import psycopg
import pytest
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from fastapi.testclient import TestClient

from estimate_api.app import app
from estimate_api.auth import AuthUnavailable, InvalidAccessToken, SupabaseJWTVerifier, get_verifier
from estimate_api.projects import get_repository

_P1 = "10000000-0000-0000-0000-000000000001"
_P2 = "10000000-0000-0000-0000-000000000002"


class _JwksHandler(BaseHTTPRequestHandler):
    jwks: bytes = b""

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/auth/v1/.well-known/jwks.json":
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(self.jwks)))
        self.end_headers()
        self.wfile.write(self.jwks)

    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture
def signing_service(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[Any, str]]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key()))
    public_jwk.update({"kid": "synthetic-key-1", "alg": "RS256", "use": "sig"})
    _JwksHandler.jwks = json.dumps({"keys": [public_jwk]}).encode()
    server = ThreadingHTTPServer(("127.0.0.1", 0), _JwksHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    issuer = f"http://127.0.0.1:{server.server_port}/auth/v1"
    monkeypatch.setenv("ESTIMATE_SUPABASE_AUTH_ISSUER", issuer)
    monkeypatch.setenv("ESTIMATE_SUPABASE_AUTH_AUDIENCE", "authenticated")
    get_verifier.cache_clear()
    get_repository.cache_clear()
    yield private_key, issuer
    get_verifier.cache_clear()
    get_repository.cache_clear()
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


def _token(key: Any, issuer: str, user: int, **overrides: Any) -> str:
    now = datetime.now(UTC)
    claims: dict[str, Any] = {
        "iss": issuer,
        "aud": "authenticated",
        "exp": now + timedelta(minutes=5),
        "iat": now,
        "sub": str(UUID(int=user)),
        "role": "authenticated",
    }
    claims.update(overrides)
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": "synthetic-key-1"})


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_verifier_checks_claims_and_signature(signing_service: tuple[Any, str]) -> None:
    key, issuer = signing_service
    verifier = SupabaseJWTVerifier(issuer, "authenticated")
    assert verifier.verify(_token(key, issuer, 1)) == UUID(int=1)
    bad_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    invalid = [
        _token(bad_key, issuer, 1),
        _token(key, issuer + "/other", 1),
        _token(key, issuer, 1, aud="other"),
        _token(key, issuer, 1, role="service_role"),
        _token(key, issuer, 1, is_anonymous=True),
        _token(key, issuer, 1, is_anonymous="false"),
        _token(key, issuer, 1, exp=datetime.now(UTC) - timedelta(seconds=1)),
        _token(key, issuer, 1, sub="not-a-uuid"),
    ]
    for token in invalid:
        with pytest.raises(InvalidAccessToken):
            verifier.verify(token)
    unsupported = jwt.encode(
        {"sub": str(UUID(int=1))}, "synthetic-only-long-random-test-key", algorithm="HS256"
    )
    with pytest.raises(InvalidAccessToken):
        verifier.verify(unsupported)

    # An unknown kid fails closed during the fetch cooldown. A verifier
    # started after the standby key is published can validate the new key.
    # All keys here are ephemeral test keys.
    next_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    next_jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(next_key.public_key()))
    next_jwk.update({"kid": "synthetic-key-2", "alg": "RS256", "use": "sig"})
    current_jwks = json.loads(_JwksHandler.jwks)
    _JwksHandler.jwks = json.dumps({"keys": [*current_jwks["keys"], next_jwk]}).encode()
    now = datetime.now(UTC)
    rotated = jwt.encode(
        {
            "iss": issuer,
            "aud": "authenticated",
            "exp": now + timedelta(minutes=5),
            "iat": now,
            "sub": str(UUID(int=2)),
            "role": "authenticated",
        },
        next_key,
        algorithm="RS256",
        headers={"kid": "synthetic-key-2"},
    )
    with pytest.raises(InvalidAccessToken):
        verifier.verify(rotated)
    assert SupabaseJWTVerifier(issuer, "authenticated").verify(rotated) == UUID(int=2)

    ec_key = ec.generate_private_key(ec.SECP256R1())
    ec_jwk = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(ec_key.public_key()))
    ec_jwk.update({"kid": "synthetic-ec", "alg": "ES256", "use": "sig"})
    published = json.loads(_JwksHandler.jwks)
    _JwksHandler.jwks = json.dumps({"keys": [*published["keys"], ec_jwk]}).encode()
    ec_token = jwt.encode(
        {
            "iss": issuer,
            "aud": "authenticated",
            "exp": now + timedelta(minutes=5),
            "iat": now,
            "sub": str(UUID(int=3)),
            "role": "authenticated",
        },
        ec_key,
        algorithm="ES256",
        headers={"kid": "synthetic-ec"},
    )
    assert SupabaseJWTVerifier(issuer, "authenticated").verify(ec_token) == UUID(int=3)

    offline = SupabaseJWTVerifier("http://127.0.0.1:1/auth/v1", "authenticated")
    with pytest.raises(AuthUnavailable):
        offline.verify(_token(key, issuer, 1))


@pytest.mark.skipif("ESTIMATE_DB_READ_DSN" not in os.environ, reason="needs disposable database")
def test_http_project_visibility(
    signing_service: tuple[Any, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    key, issuer = signing_service
    monkeypatch.setenv(
        "ESTIMATE_INTERACTIVE_ALLOWED_SUBJECTS",
        json.dumps([str(UUID(int=user)) for user in (1, 2, 3, 4, 5)]),
    )
    with TestClient(app) as client:
        assert client.get("/projects").status_code == 401
        not_admitted = _headers(_token(key, issuer, 6))
        assert client.get("/projects", headers=not_admitted).status_code == 403
        assert client.get(f"/projects/{_P1}", headers=not_admitted).status_code == 403
        monkeypatch.delenv("ESTIMATE_INTERACTIVE_ALLOWED_SUBJECTS")
        assert client.get("/projects", headers=_headers(_token(key, issuer, 1))).status_code == 403
        monkeypatch.setenv(
            "ESTIMATE_INTERACTIVE_ALLOWED_SUBJECTS",
            json.dumps([str(UUID(int=user)) for user in (1, 2, 3, 4, 5)]),
        )
        expected = {1: (_P1, "owner"), 2: (_P2, "owner"), 3: (_P1, "viewer"), 5: (_P1, "editor")}
        for user, (project_id, role) in expected.items():
            response = client.get("/projects", headers=_headers(_token(key, issuer, user)))
            assert response.status_code == 200
            visible = [(p["id"], p["access_role"]) for p in response.json()["items"]]
            assert visible[0] == (project_id, role)
            assert len(visible) == (2 if user == 1 else 1)
            assert response.json()["next_cursor"] is None
            detail = client.get(
                f"/projects/{project_id}", headers=_headers(_token(key, issuer, user))
            )
            assert detail.status_code == 200
            assert detail.json()["access_role"] == role
        outsider = _token(key, issuer, 4, user_metadata={"sub": str(UUID(int=1))})
        assert client.get("/projects", headers=_headers(outsider)).json() == {
            "items": [],
            "next_cursor": None,
        }
        owner_headers = _headers(_token(key, issuer, 1))
        first = client.get("/projects?limit=1", headers=owner_headers)
        assert first.status_code == 200
        assert [item["id"] for item in first.json()["items"]] == [_P1]
        assert first.json()["next_cursor"] == _P1
        second = client.get("/projects", params={"limit": 1, "cursor": _P1}, headers=owner_headers)
        assert [item["id"] for item in second.json()["items"]] == [
            "10000000-0000-0000-0000-000000000003"
        ]
        assert second.json()["next_cursor"] is None
        assert client.get("/projects?limit=0", headers=owner_headers).status_code == 422
        assert client.get("/projects?limit=101", headers=owner_headers).status_code == 422
        # One TestClient serves different valid identities without carrying the
        # previous request's database role or actor claim into the next request.
        assert client.get("/projects", headers=_headers(outsider)).json()["items"] == []
        assert len(client.get("/projects", headers=owner_headers).json()["items"]) == 2
        # Reusing the same still-valid token cannot retain access after membership removal.
        member_headers = _headers(_token(key, issuer, 3))
        assert len(client.get("/projects", headers=member_headers).json()["items"]) == 1
        with psycopg.connect(os.environ["ESTIMATE_DB_TEST_ADMIN_DSN"], autocommit=True) as conn:
            conn.execute(
                "select set_config('request.jwt.claim.sub', %s, false)", (str(UUID(int=1)),)
            )
            conn.execute(
                "delete from public.project_memberships where project_id = %s and user_id = %s",
                (_P1, str(UUID(int=3))),
            )
        assert client.get("/projects", headers=member_headers).json()["items"] == []
        assert client.get(f"/projects/{_P1}", headers=member_headers).status_code == 404
        assert client.get(f"/projects/{_P1}", headers=_headers(outsider)).status_code == 404
        assert client.get("/projects/not-a-uuid", headers=_headers(outsider)).status_code == 422
        wrong_audience = _token(key, issuer, 1, aud="other")
        assert client.get("/projects", headers=_headers(wrong_audience)).status_code == 401
        monkeypatch.setenv("ESTIMATE_INTERACTIVE_ALLOWED_SUBJECTS", "not-json")
        assert client.get("/projects", headers=owner_headers).status_code == 503
        monkeypatch.setenv(
            "ESTIMATE_INTERACTIVE_ALLOWED_SUBJECTS",
            json.dumps([str(UUID(int=user)) for user in (1, 2, 3, 4, 5)]),
        )
        read_dsn = os.environ["ESTIMATE_DB_READ_DSN"]
        monkeypatch.setenv("ESTIMATE_DB_READ_DSN", os.environ["ESTIMATE_DB_TEST_ADMIN_DSN"])
        get_repository.cache_clear()
        assert client.get("/projects", headers=owner_headers).status_code == 503
        monkeypatch.setenv("ESTIMATE_DB_READ_DSN", read_dsn)
        get_repository.cache_clear()
        monkeypatch.setenv("ESTIMATE_SUPABASE_AUTH_ISSUER", "http://127.0.0.1:1/auth/v1")
        get_verifier.cache_clear()
        bearer = _token(key, issuer, 1)
        unavailable = client.get("/projects", headers=_headers(bearer))
        assert unavailable.status_code == 503
        assert bearer not in unavailable.text
