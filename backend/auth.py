"""
Zitadel JWT verification for the ZuriBot API.

- Fetches the OIDC discovery doc + JWKS lazily, caches both in memory.
- Verifies RS256 signatures, issuer, and expiry.
- Audience check is lenient: Zitadel's `aud` for SPA tokens contains the
  project's resource id and/or client ids. We accept any token issued by
  our configured issuer; tighten via `ZITADEL_EXPECTED_AUDIENCE` once the
  project id is stable.
"""

import logging
import os
import threading
import time
from typing import Any, Optional

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger("zuribot.auth")

ZITADEL_ISSUER = os.environ.get("ZITADEL_ISSUER", "http://localhost:8080").rstrip("/")
ZITADEL_EXPECTED_AUDIENCE = os.environ.get("ZITADEL_EXPECTED_AUDIENCE")  # optional
AUTH_REQUIRED = os.environ.get("ZURIBOT_AUTH_REQUIRED", "true").lower() != "false"

_JWKS_TTL_SECONDS = 3600
_jwks_cache: dict[str, Any] = {"fetched_at": 0.0, "keys_by_kid": {}}
_jwks_lock = threading.Lock()

_bearer = HTTPBearer(auto_error=False)


def _fetch_jwks() -> dict[str, Any]:
    with httpx.Client(timeout=5.0) as client:
        disc = client.get(f"{ZITADEL_ISSUER}/.well-known/openid-configuration").json()
        jwks_uri = disc["jwks_uri"]
        jwks = client.get(jwks_uri).json()
    keys_by_kid = {k["kid"]: k for k in jwks.get("keys", [])}
    return {"fetched_at": time.time(), "keys_by_kid": keys_by_kid}


def _get_signing_key(kid: str):
    with _jwks_lock:
        stale = time.time() - _jwks_cache["fetched_at"] > _JWKS_TTL_SECONDS
        if stale or kid not in _jwks_cache["keys_by_kid"]:
            _jwks_cache.update(_fetch_jwks())
        jwk = _jwks_cache["keys_by_kid"].get(kid)
    if not jwk:
        raise HTTPException(status_code=401, detail="Unknown signing key")
    return jwt.algorithms.RSAAlgorithm.from_jwk(jwk)


def verify_access_token(token: str) -> dict[str, Any]:
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Malformed token: {e}")

    kid = header.get("kid")
    if not kid:
        raise HTTPException(status_code=401, detail="Missing kid in token header")

    key = _get_signing_key(kid)
    options = {"verify_aud": bool(ZITADEL_EXPECTED_AUDIENCE)}
    try:
        claims = jwt.decode(
            token,
            key=key,
            algorithms=["RS256"],
            issuer=ZITADEL_ISSUER,
            audience=ZITADEL_EXPECTED_AUDIENCE if ZITADEL_EXPECTED_AUDIENCE else None,
            options=options,
        )
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
    return claims


async def require_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> dict[str, Any]:
    if not AUTH_REQUIRED:
        return {"sub": "anonymous", "_auth_disabled": True}
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return verify_access_token(creds.credentials)
