"""
Helpers / Miscellaneous Utilities
General-purpose utility functions used across the application.
"""

import re
import uuid
from datetime import datetime, timezone
from typing import Any


def generate_uuid() -> str:
    """Generate a new UUID4 string."""
    return str(uuid.uuid4())


def utcnow() -> datetime:
    """Return the current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text


def truncate_string(text: str, max_length: int = 200, suffix: str = "...") -> str:
    """Truncate a string to max_length characters."""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert a value to int, returning default on failure."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert a value to float, returning default on failure."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def flatten_list(nested: list) -> list:
    """Flatten one level of a nested list."""
    return [item for sublist in nested for item in sublist]


def dict_to_str(d: dict) -> str:
    """Convert a dict to a readable key=value string."""
    return ", ".join(f"{k}={v}" for k, v in d.items())


def mask_email(email: str) -> str:
    """Partially mask an email address for display (e.g., j***@gmail.com)."""
    if "@" not in email:
        return email
    local, domain = email.split("@", 1)
    masked = local[0] + "***" if len(local) > 1 else "***"
    return f"{masked}@{domain}"


def parse_bool(value: Any) -> bool:
    """Parse a value as boolean (handles strings like 'true', '1', 'yes')."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes", "on")
    return bool(value)
