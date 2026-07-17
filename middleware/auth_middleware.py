"""
Authentication Middleware — NGO Volunteer Management System
===========================================================
JWT-based route protection with full entity awareness (user vs admin).

Decorators
----------
@require_auth          — Any authenticated user (volunteer / staff / admin)
@require_admin_auth    — Any authenticated admin (super_admin / admin / moderator)
@require_role(...)     — Authenticated user with specific role(s)
@require_admin_role(.) — Authenticated admin with specific role(s)
@optional_auth         — Attempt auth but allow anonymous; injects None if unauthed

All decorators inject `current_user` (or `current_admin`) as the FIRST
positional argument of the decorated view function, after Flask's
view-function positional args (e.g. URL params come after).

Token entity handling
---------------------
Each JWT payload carries an `entity` claim: "user" | "admin".
The middleware uses this to load from the correct MongoDB collection,
preventing users from using admin tokens on user routes and vice-versa.
"""

import logging
from functools import wraps
from flask import request

from models.user  import UserModel
from models.admin import AdminModel
from utils.jwt_helper import decode_token, is_token_blacklisted
from utils.response   import error_response

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# Internal helpers
# ══════════════════════════════════════════════════════════════════════════════

def _extract_token() -> str | None:
    """
    Extract the raw Bearer token from the Authorization header.
    Also supports X-Access-Token header as a fallback (useful for testing tools).
    """
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth.split(" ", 1)[1].strip()
    # Fallback header
    token = request.headers.get("X-Access-Token", "").strip()
    return token or None


def _load_entity(payload: dict) -> dict | None:
    """
    Load the correct document (user or admin) from MongoDB based on
    the `entity` claim inside the JWT payload.

    Returns:
        A MongoDB document dict, or None if not found / wrong entity.
    """
    entity = payload.get("entity", "user")
    sub    = payload.get("sub")

    if entity == "admin":
        return AdminModel.find_by_id(sub)
    else:
        return UserModel.find_by_id(sub)


def _is_account_active(entity: str, doc: dict) -> bool:
    """Check whether the loaded account is active."""
    if entity == "admin":
        return doc.get("is_active", False)
    else:
        return doc.get("status", "inactive") == "active"


def _authenticate(require_entity: str = None) -> tuple[dict | None, any]:
    """
    Core authentication flow.

    Args:
        require_entity: If "user" or "admin", reject tokens from the other entity.

    Returns:
        (document_dict, None)  on success
        (None, error_response) on failure
    """
    token = _extract_token()
    if not token:
        return None, error_response(
            "Authorization token missing. Include 'Authorization: Bearer <token>'.", 401
        )

    if is_token_blacklisted(token):
        return None, error_response(
            "Token has been revoked. Please log in again.", 401
        )

    payload = decode_token(token)
    if not payload:
        return None, error_response(
            "Invalid or expired token. Please log in again.", 401
        )

    if payload.get("type") != "access":
        return None, error_response(
            "Wrong token type. Use your access token, not a refresh token.", 401
        )

    entity = payload.get("entity", "user")
    if require_entity and entity != require_entity:
        return None, error_response(
            f"This endpoint requires a {require_entity} token.", 403
        )

    doc = _load_entity(payload)
    if not doc:
        return None, error_response("Account not found.", 401)

    if not _is_account_active(entity, doc):
        return None, error_response(
            "Your account is inactive or suspended. Please contact support.", 403
        )

    return doc, None


# ══════════════════════════════════════════════════════════════════════════════
# Public decorators
# ══════════════════════════════════════════════════════════════════════════════

def require_auth(f):
    """
    Enforce authentication for any entity (user or admin).
    Injects the loaded MongoDB document as `current_user` (first arg).

    Usage:
        @require_auth
        def my_view(current_user, ...):
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        doc, err = _authenticate()
        if err:
            return err
        return f(doc, *args, **kwargs)
    return decorated


def require_user_auth(f):
    """
    Enforce authentication for USERS only (not admins).
    Rejects admin tokens with 403.

    Usage:
        @require_user_auth
        def my_view(current_user, ...):
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        doc, err = _authenticate(require_entity="user")
        if err:
            return err
        return f(doc, *args, **kwargs)
    return decorated


def require_admin_auth(f):
    """
    Enforce authentication for ADMINS only (not regular users).
    Rejects user tokens with 403.

    Usage:
        @require_admin_auth
        def my_view(current_admin, ...):
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        doc, err = _authenticate(require_entity="admin")
        if err:
            return err
        return f(doc, *args, **kwargs)
    return decorated


def require_role(*roles: str):
    """
    Enforce that the authenticated entity has one of the given roles.
    Must be stacked AFTER @require_auth / @require_user_auth.

    Usage:
        @require_auth
        @require_role("admin", "staff")
        def my_view(current_user, ...):
    """
    def decorator(f):
        @wraps(f)
        def decorated(current_user, *args, **kwargs):
            if current_user.get("role") not in roles:
                allowed = ", ".join(roles)
                return error_response(
                    f"Access denied. Required role(s): {allowed}.", 403
                )
            return f(current_user, *args, **kwargs)
        return decorated
    return decorator


def require_admin_role(*roles: str):
    """
    Enforce admin authentication AND that the admin has one of the given roles.
    This is a COMBINED decorator (wraps both require_admin_auth + role check).

    Usage:
        @require_admin_role("super_admin")
        def my_view(current_admin, ...):
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            doc, err = _authenticate(require_entity="admin")
            if err:
                return err
            if doc.get("role") not in roles:
                allowed = ", ".join(roles)
                return error_response(
                    f"Access denied. Required admin role(s): {allowed}.", 403
                )
            return f(doc, *args, **kwargs)
        return decorated
    return decorator


def optional_auth(f):
    """
    Attempt authentication but allow unauthenticated access.
    Injects the entity document or None as the first argument.

    Usage:
        @optional_auth
        def my_view(current_user, ...):   # current_user may be None
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        current_entity = None
        token = _extract_token()
        if token and not is_token_blacklisted(token):
            payload = decode_token(token)
            if payload and payload.get("type") == "access":
                doc = _load_entity(payload)
                if doc and _is_account_active(payload.get("entity", "user"), doc):
                    current_entity = doc
        return f(current_entity, *args, **kwargs)
    return decorated


# ══════════════════════════════════════════════════════════════════════════════
# Convenience combos
# ══════════════════════════════════════════════════════════════════════════════

def require_super_admin(f):
    """Shortcut: @require_admin_role("super_admin")"""
    return require_admin_role("super_admin")(f)


def require_staff_or_admin(f):
    """Shortcut: allow staff, admin, or super_admin users."""
    @wraps(f)
    def decorated(*args, **kwargs):
        doc, err = _authenticate()
        if err:
            return err
        if doc.get("role") not in ("staff", "admin", "super_admin"):
            return error_response("Access denied. Staff or admin required.", 403)
        return f(doc, *args, **kwargs)
    return decorated
