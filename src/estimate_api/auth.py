"""Verify Supabase access tokens before any project database read."""

import os
from functools import lru_cache
from typing import Annotated
from urllib.parse import urlparse
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError

_bearer = HTTPBearer(auto_error=False, description="Supabase Auth access token")
_ALGORITHMS = ("RS256", "ES256")


class InvalidAccessToken(Exception):
    """The request did not carry a valid user access token."""


class AuthUnavailable(Exception):
    """The configured signing-key service is not currently reachable."""


class SupabaseJWTVerifier:
    """Validate a token against keys from one configured Supabase Auth issuer."""

    def __init__(self, issuer: str, audience: str) -> None:
        parsed = urlparse(issuer)
        if parsed.scheme != "https" and not (
            parsed.scheme == "http" and parsed.hostname in ("127.0.0.1", "localhost")
        ):
            raise ValueError("A fixed HTTPS issuer or local test issuer is required")
        if parsed.query or parsed.fragment or not parsed.netloc or not audience:
            raise ValueError("Issuer and audience must be fixed configuration")
        self.issuer = issuer.rstrip("/")
        self.audience = audience
        # Supabase's edge cache is ten minutes; do not cache keys longer here.
        self._keys = PyJWKClient(
            f"{self.issuer}/.well-known/jwks.json",
            cache_jwk_set=True,
            lifespan=600,
            timeout=3,
            cooldown_duration=30,
        )

    def verify(self, token: str) -> UUID:
        if not token or len(token) > 8192:
            raise InvalidAccessToken
        try:
            header = jwt.get_unverified_header(token)
            algorithm = header.get("alg")
            kid = header.get("kid")
            if algorithm not in _ALGORITHMS or not isinstance(kid, str) or not kid:
                raise InvalidAccessToken
            key = self._keys.get_signing_key_from_jwt(token)
            if key.algorithm_name != algorithm:
                raise InvalidAccessToken
            claims = jwt.decode(
                token,
                key.key,
                algorithms=[algorithm],
                issuer=self.issuer,
                audience=self.audience,
                options={"require": ["iss", "aud", "exp", "iat", "sub", "role"]},
                leeway=0,
            )
            if claims.get("role") != "authenticated" or not isinstance(claims.get("sub"), str):
                raise InvalidAccessToken
            anonymous = claims.get("is_anonymous")
            if anonymous is not None and anonymous is not False:
                raise InvalidAccessToken
            return UUID(claims["sub"])
        except PyJWKClientConnectionError as exc:
            raise AuthUnavailable from exc
        except (jwt.InvalidTokenError, PyJWKClientError, ValueError, TypeError) as exc:
            raise InvalidAccessToken from exc


@lru_cache(maxsize=1)
def get_verifier() -> SupabaseJWTVerifier:
    issuer = os.environ.get("ESTIMATE_SUPABASE_AUTH_ISSUER")
    audience = os.environ.get("ESTIMATE_SUPABASE_AUTH_AUDIENCE")
    if not issuer or not audience:
        raise AuthUnavailable
    try:
        return SupabaseJWTVerifier(issuer, audience)
    except ValueError as exc:
        raise AuthUnavailable from exc


def get_actor(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> UUID:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Bearer token required")
    try:
        return get_verifier().verify(credentials.credentials)
    except InvalidAccessToken:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid access token") from None
    except AuthUnavailable:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Authentication unavailable"
        ) from None
