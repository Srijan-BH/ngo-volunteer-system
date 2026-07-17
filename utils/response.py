"""
Response Utilities — NGO Volunteer Management System
====================================================
Standardised JSON response builders ensuring every API endpoint
returns the same envelope structure.

Success envelope
----------------
{
  "status":  "success",
  "message": "...",
  "data":    { ... }        ← only when data is not None
}

Error envelope
--------------
{
  "status":  "error",
  "code":    <HTTP status int>,
  "message": "...",
  "errors":  [ "..." ]     ← only when multiple field-level errors exist
}

Paginated envelope
------------------
{
  "status":  "success",
  "message": "...",
  "data": {
    "items": [ ... ],
    "pagination": {
      "page":        <int>,
      "page_size":   <int>,
      "total_items": <int>,
      "total_pages": <int>,
      "has_next":    <bool>,
      "has_prev":    <bool>
    },
    ...extra fields...
  }
}
"""

import math
from flask import jsonify


# ─── Success ──────────────────────────────────────────────────────────────────

def success_response(
    data=None,
    message: str = "Success.",
    status_code: int = 200,
    meta: dict = None,
) -> tuple:
    """
    Build a standardised success response.

    Args:
        data:        Any JSON-serialisable object (dict, list, None).
        message:     Human-readable result description.
        status_code: HTTP status code (default 200).
        meta:        Optional top-level metadata (e.g. token expiry info).

    Returns:
        (flask.Response, int) tuple.
    """
    body = {
        "status":  "success",
        "message": message,
    }
    if data is not None:
        body["data"] = data
    if meta:
        body["meta"] = meta
    return jsonify(body), status_code


# ─── Error ────────────────────────────────────────────────────────────────────

def error_response(
    message: str = "An error occurred.",
    status_code: int = 400,
    errors: list = None,
    field: str = None,
) -> tuple:
    """
    Build a standardised error response.

    Args:
        message:     Primary error description.
        status_code: HTTP error code.
        errors:      List of additional field-level error strings.
        field:       Optional field name that caused the error.

    Returns:
        (flask.Response, int) tuple.
    """
    body = {
        "status":  "error",
        "code":    status_code,
        "message": message,
    }
    if errors:
        body["errors"] = errors
    if field:
        body["field"] = field
    return jsonify(body), status_code


def validation_error_response(errors: list[str]) -> tuple:
    """
    Shortcut for 422 Unprocessable Entity with a list of validation errors.
    The first error becomes the primary message.
    """
    return error_response(
        message=errors[0] if errors else "Validation failed.",
        status_code=422,
        errors=errors if len(errors) > 1 else None,
    )


# ─── Paginated ────────────────────────────────────────────────────────────────

def paginated_response(
    items: list,
    total: int,
    page: int,
    page_size: int,
    message: str = "Data retrieved successfully.",
    extra: dict = None,
) -> tuple:
    """
    Build a standardised paginated response.

    Args:
        items:     List of serialised documents for the current page.
        total:     Total number of matching documents.
        page:      Current page number (1-indexed).
        page_size: Number of items per page.
        message:   Human-readable result description.
        extra:     Any extra keys to merge into `data` (e.g. unread_count).

    Returns:
        (flask.Response, 200) tuple.
    """
    total_pages = math.ceil(total / page_size) if page_size > 0 else 0
    body = {
        "status":  "success",
        "message": message,
        "data": {
            "items": items,
            "pagination": {
                "page":        page,
                "page_size":   page_size,
                "total_items": total,
                "total_pages": total_pages,
                "has_next":    page < total_pages,
                "has_prev":    page > 1,
            },
        },
    }
    if extra:
        body["data"].update(extra)
    return jsonify(body), 200


# ─── Auth-specific convenience builders ──────────────────────────────────────

def auth_success_response(
    entity: dict,
    access_token: str,
    refresh_token: str,
    message: str = "Authentication successful.",
    status_code: int = 200,
    extra: dict = None,
) -> tuple:
    """
    Standard response for login / register / token-refresh flows.

    Args:
        entity:        Serialised user or admin document.
        access_token:  Fresh access JWT.
        refresh_token: Fresh refresh JWT.
        message:       Human-readable message.
        status_code:   HTTP code (200 for login, 201 for register).
        extra:         Any extra keys to merge into `data`.

    Returns:
        (flask.Response, int) tuple.
    """
    data = {
        "access_token":  access_token,
        "refresh_token": refresh_token,
        "token_type":    "Bearer",
        "user":          entity,
    }
    if extra:
        data.update(extra)
    return success_response(data=data, message=message, status_code=status_code)


def token_response(access_token: str, message: str = "Token refreshed.") -> tuple:
    """Minimal response for token-refresh endpoint."""
    return success_response(
        data={"access_token": access_token, "token_type": "Bearer"},
        message=message,
    )
