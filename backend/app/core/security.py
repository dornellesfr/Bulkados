import logging
import time
from uuid import UUID

import httpx
import jwt
from jwt import PyJWK, PyJWKSet

from app.core.config import Settings
from app.core.errors import InvalidTokenError

logger = logging.getLogger(__name__)

_JWKS_TTL_SECONDS = 600
_jwks_fetched_at = 0.0
_jwks_by_kid: dict[str, PyJWK] = {}


async def user_id_from_access_token(token: str, settings: Settings) -> UUID:
    algorithm = _algorithm(token)
    issuer = _issuer(settings)
    try:
        if algorithm == "HS256":
            secret = settings.supabase_jwt_secret.get_secret_value()
            if not secret:
                raise InvalidTokenError
            decoded: object = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                audience="authenticated",
                issuer=issuer,
                leeway=10,
            )
        elif algorithm in {"RS256", "ES256"}:
            signing_key = await _signing_key(token, settings)
            decoded = jwt.decode(
                token,
                signing_key.key,
                algorithms=[algorithm],
                audience="authenticated",
                issuer=issuer,
                leeway=10,
            )
        else:
            raise InvalidTokenError
    except jwt.PyJWTError as exc:
        raise InvalidTokenError from exc
    return _subject(decoded)


def _algorithm(token: str) -> str:
    try:
        header: object = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise InvalidTokenError from exc
    if not isinstance(header, dict):
        raise InvalidTokenError
    algorithm = header.get("alg")
    if not isinstance(algorithm, str):
        raise InvalidTokenError
    return algorithm


def _issuer(settings: Settings) -> str:
    base_url = settings.supabase_url.rstrip("/")
    if not base_url:
        raise InvalidTokenError
    return f"{base_url}/auth/v1"


def _subject(decoded: object) -> UUID:
    if not isinstance(decoded, dict):
        raise InvalidTokenError
    subject = decoded.get("sub")
    if not isinstance(subject, str):
        raise InvalidTokenError
    try:
        return UUID(subject)
    except ValueError as exc:
        raise InvalidTokenError from exc


async def _signing_key(token: str, settings: Settings) -> PyJWK:
    kid = _key_id(token)
    keys = await _jwks(settings)
    key = keys.get(kid)
    if key is None:
        raise InvalidTokenError
    return key


def _key_id(token: str) -> str:
    try:
        header: object = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise InvalidTokenError from exc
    if not isinstance(header, dict):
        raise InvalidTokenError
    kid = header.get("kid")
    if not isinstance(kid, str) or not kid:
        raise InvalidTokenError
    return kid


async def _jwks(settings: Settings) -> dict[str, PyJWK]:
    global _jwks_fetched_at
    now = time.monotonic()
    if _jwks_by_kid and now - _jwks_fetched_at < _JWKS_TTL_SECONDS:
        return _jwks_by_kid
    url = settings.supabase_jwks_url or f"{_issuer(settings)}/.well-known/jwks.json"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url)
            response.raise_for_status()
            payload: object = response.json()
    except httpx.HTTPError as exc:
        logger.warning("jwks fetch failed")
        raise InvalidTokenError from exc
    if not isinstance(payload, dict):
        raise InvalidTokenError
    document = {key: value for key, value in payload.items() if isinstance(key, str)}
    try:
        parsed = PyJWKSet.from_dict(document)
    except jwt.PyJWTError as exc:
        raise InvalidTokenError from exc
    _jwks_by_kid.clear()
    for key in parsed.keys:
        if key.key_id:
            _jwks_by_kid[key.key_id] = key
    _jwks_fetched_at = now
    return _jwks_by_kid
