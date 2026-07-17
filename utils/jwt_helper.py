"""
JWT Helper — NGO Volunteer Management System
============================================
Handles:
  • Access token generation          (short-lived, 24h / 30 days remember-me)
  • Refresh token generation         (long-lived, 30 days)
  • Admin token generation           (separate claim)
  • Token decoding & validation
  • Token blacklisting               (MongoDB collection with TTL)
  • JTI-based unique token identity

Token payload structure
-----------------------
  Access token  : { sub, email, role, entity, type:"access",  jti, iat, exp }
  Refresh token : { sub, entity, type:"refresh", jti, iat, exp }
  Reset token   : { sub, purpose:"password_reset", jti, iat, exp }

`entity` distinguishes "user" vs "admin" so the middleware can load from
the correct collection without ambiguity.
"""

import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import jwt
from flask import current_app

from database.connection import get_collection

logger = logging.getLogger(__name__)

BLACKLIST_COLLECTION = "token_blacklist"

# ─── Internal helpers ─────────────────────────────────────────────────────────

def _secret() -> str:
    return current_app.config.get("JWT_SECRET_KEY", "fallback-secret")

def _algo() -> str:
    return current_app.config.get("JWT_ALGORITHM", "HS256")

def _new_jti() -> str:
    """Generate a unique JWT ID (JTI) for each token."""
    return str(uuid.uuid4())


# ─── User token generators ────────────────────────────────────────────────────

def generate_access_token(user: dict, remember_me: bool = False) -> str:
    """
    Generate a signed JWT access token for a user.

    Args:
        user:        MongoDB user document.
        remember_me: If True, extends expiry to 30 days instead of default 24 h.

    Returns:
        Signed JWT string.
    """
    now = datetime.now(timezone.utc)
    if remember_me:
        expires = now + timedelta(days=30)
    else:
        expires = now + current_app.config.get("JWT_ACCESS_TOKEN_EXPIRES", timedelta(hours=24))

    payload = {
        "sub":    str(user["_id"]),
        "email":  user["email"],
        "role":   user["role"],
        "entity": "user",          # ← distinguishes from admin tokens
        "type":   "access",
        "jti":    _new_jti(),
        "iat":    now,
        "exp":    expires,
    }
    return jwt.encode(payload, _secret(), algorithm=_algo())


def generate_refresh_token(user: dict, remember_me: bool = False) -> str:
    """
    Generate a signed JWT refresh token for a user.

    Args:
        user:        MongoDB user document.
        remember_me: If True, extends expiry to 90 days.

    Returns:
        Signed JWT string.
    """
    now = datetime.now(timezone.utc)
    if remember_me:
        expires = now + timedelta(days=90)
    else:
        expires = now + current_app.config.get("JWT_REFRESH_TOKEN_EXPIRES", timedelta(days=30))

    payload = {
        "sub":    str(user["_id"]),
        "entity": "user",
        "type":   "refresh",
        "jti":    _new_jti(),
        "iat":    now,
        "exp":    expires,
    }
    return jwt.encode(payload, _secret(), algorithm=_algo())


# ─── Admin token generators ───────────────────────────────────────────────────

def generate_admin_access_token(admin: dict, remember_me: bool = False) -> str:
    """
    Generate a signed JWT access token for an admin.
    Uses entity="admin" so middleware routes to AdminModel.
    """
    now = datetime.now(timezone.utc)
    if remember_me:
        expires = now + timedelta(days=7)          # admins: 7-day max remember-me
    else:
        expires = now + timedelta(hours=8)         # admins: shorter default session

    payload = {
        "sub":    str(admin["_id"]),
        "email":  admin["email"],
        "role":   admin["role"],
        "entity": "admin",
        "type":   "access",
        "jti":    _new_jti(),
        "iat":    now,
        "exp":    expires,
    }
    return jwt.encode(payload, _secret(), algorithm=_algo())


def generate_admin_refresh_token(admin: dict) -> str:
    """Generate a refresh token for an admin (7 days)."""
    now     = datetime.now(timezone.utc)
    expires = now + timedelta(days=7)
    payload = {
        "sub":    str(admin["_id"]),
        "entity": "admin",
        "type":   "refresh",
        "jti":    _new_jti(),
        "iat":    now,
        "exp":    expires,
    }
    return jwt.encode(payload, _secret(), algorithm=_algo())


# ─── Password-reset token ─────────────────────────────────────────────────────

def generate_password_reset_token(user_id: str, entity: str = "user") -> str:
    """
    Generate a short-lived (15 min) password-reset JWT.

    Args:
        user_id: The user's or admin's _id string.
        entity:  "user" or "admin".

    Returns:
        Signed JWT string.
    """
    now     = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=15)
    payload = {
        "sub":     user_id,
        "entity":  entity,
        "purpose": "password_reset",
        "jti":     _new_jti(),
        "iat":     now,
        "exp":     expires,
    }
    return jwt.encode(payload, _secret(), algorithm=_algo())


def verify_password_reset_token(token: str) -> Optional[dict]:
    """
    Decode and validate a password-reset token.

    Returns:
        Payload dict if valid, else None.
    """
    payload = decode_token(token)
    if not payload:
        return None
    if payload.get("purpose") != "password_reset":
        return None
    if is_token_blacklisted(token):
        return None
    return payload


# ─── Decode & validate ────────────────────────────────────────────────────────

def decode_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT (any type).

    Returns:
        Payload dict on success, None on any failure.
    """
    try:
        return jwt.decode(token, _secret(), algorithms=[_algo()])
    except jwt.ExpiredSignatureError:
        logger.debug("JWT expired.")
        return None
    except jwt.InvalidTokenError as exc:
        logger.debug(f"Invalid JWT: {exc}")
        return None


# ─── Blacklist ────────────────────────────────────────────────────────────────

def blacklist_token(token: str) -> None:
    """
    Revoke a token by storing its JTI in the token_blacklist collection.
    The TTL index on `blacklisted_at` auto-cleans entries after 90 days.
    """
    payload = decode_token(token)
    jti     = payload.get("jti", token[:64]) if payload else token[:64]

    get_collection(BLACKLIST_COLLECTION).update_one(
        {"jti": jti},
        {
            "$set": {
                "jti":            jti,
                "blacklisted_at": datetime.now(timezone.utc),
                "token_prefix":   token[:32],
                "entity":         payload.get("entity", "unknown") if payload else "unknown",
                "type":           payload.get("type",   "unknown") if payload else "unknown",
            }
        },
        upsert=True,
    )
    logger.info(f"Token blacklisted: jti={jti}")


def blacklist_token_by_jti(jti: str, entity: str = "unknown") -> None:
    """Revoke a token directly by its known JTI (used in logout-all scenarios)."""
    get_collection(BLACKLIST_COLLECTION).update_one(
        {"jti": jti},
        {
            "$set": {
                "jti":            jti,
                "blacklisted_at": datetime.now(timezone.utc),
                "entity":         entity,
            }
        },
        upsert=True,
    )


def is_token_blacklisted(token: str) -> bool:
    """
    Check if a token's JTI is in the blacklist.
    Treats invalid / expired tokens as blacklisted (returns True).
    """
    payload = decode_token(token)
    if not payload:
        return True
    jti = payload.get("jti", token[:64])
    return get_collection(BLACKLIST_COLLECTION).find_one({"jti": jti}) is not None


def is_jti_blacklisted(jti: str) -> bool:
    """Check blacklist by raw JTI string."""
    return get_collection(BLACKLIST_COLLECTION).find_one({"jti": jti}) is not None


# ─── Token introspection helpers ──────────────────────────────────────────────

def get_token_entity(token: str) -> Optional[str]:
    """Return "user" | "admin" from a token, or None if invalid."""
    payload = decode_token(token)
    return payload.get("entity") if payload else None


def get_token_payload_from_request(request) -> Optional[dict]:
    """
    Extract and decode the Bearer token from a Flask request.
    Returns the payload dict or None.
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth.split(" ", 1)[1].strip()
    if is_token_blacklisted(token):
        return None
    return decode_token(token)
