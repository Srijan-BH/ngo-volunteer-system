"""
Security Utilities
Provides functions for input sanitization to prevent database injection and XSS.
"""

import re
from typing import Any, Dict, List, Union

def sanitize_mongo_input(value: Any) -> Any:
    """
    Recursively sanitize inputs to prevent MongoDB operator injection.
    Strips out keys starting with '$' which are MongoDB operators.
    """
    if isinstance(value, dict):
        # Create a new dictionary to avoid modifying the original during iteration
        sanitized_dict = {}
        for k, v in value.items():
            if not isinstance(k, str) or not k.startswith('$'):
                sanitized_dict[k] = sanitize_mongo_input(v)
        return sanitized_dict
    elif isinstance(value, list):
        return [sanitize_mongo_input(item) for item in value]
    elif isinstance(value, str):
        # Basic XSS mitigation (HTML encoding) could go here if returning directly to templates without Jinja2 escaping,
        # but Jinja2 handles XSS on the frontend. We just want to prevent DB injection here.
        # Ensure it's not trying to be a JSON object string with operators.
        return value.strip()
    return value

def is_strong_password(password: str) -> bool:
    """
    Enforce strong password policy:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    """
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"\d", password):
        return False
    return True

import bcrypt

def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    salt = bcrypt.gensalt()
    # Hash and decode to string for MongoDB storage
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False
