"""
Validators — NGO Volunteer Management System
=============================================
Comprehensive input validation for all auth and API operations.

Covers:
  • Required field presence
  • Email format (RFC-5321 compatible regex)
  • Mobile number (E.164 / Indian formats)
  • Password strength (configurable rules)
  • Confirm-password matching
  • ObjectId format
  • URL format
  • Integer range
  • String length
  • Name validation
  • Date/time format
"""

import re
from typing import Optional


# ══════════════════════════════════════════════════════════════════════════════
# Required Fields
# ══════════════════════════════════════════════════════════════════════════════

def validate_required_fields(data: dict, required: list[str]) -> Optional[str]:
    """
    Check that all required keys are present and non-empty in `data`.

    Returns:
        An error message string on failure, or None on success.
    """
    missing = [f for f in required if not str(data.get(f, "")).strip()]
    if missing:
        return f"Missing or empty required field(s): {', '.join(missing)}."
    return None


# ══════════════════════════════════════════════════════════════════════════════
# Email
# ══════════════════════════════════════════════════════════════════════════════

# RFC-5321 compatible (handles sub-domains, plus addressing, etc.)
_EMAIL_RE = re.compile(
    r"^(?!\.)[a-zA-Z0-9._%+\-]{1,64}"
    r"@"
    r"(?:[a-zA-Z0-9\-]{1,63}\.){1,8}"
    r"[a-zA-Z]{2,63}$"
)

def validate_email(email: str) -> bool:
    """Return True if the email address has a valid format."""
    email = email.strip()
    if len(email) > 254:
        return False
    return bool(_EMAIL_RE.match(email))

def validate_email_with_message(email: str) -> Optional[str]:
    """Return an error string if invalid, else None."""
    if not email or not email.strip():
        return "Email address is required."
    if not validate_email(email):
        return "Invalid email address format."
    return None


# ══════════════════════════════════════════════════════════════════════════════
# Mobile Number
# ══════════════════════════════════════════════════════════════════════════════

# Accepts: +91XXXXXXXXXX  |  91XXXXXXXXXX  |  0XXXXXXXXXX  |  XXXXXXXXXX (10 digits)
_MOBILE_RE = re.compile(
    r"^(?:\+?91|0)?[6-9]\d{9}$"          # Indian mobiles
    r"|"
    r"^\+?[1-9]\d{6,14}$"               # International (E.164 7–15 digits)
)

def validate_mobile(mobile: str) -> bool:
    """Return True if the mobile number has a valid format."""
    cleaned = re.sub(r"[\s\-()]", "", mobile.strip())
    return bool(_MOBILE_RE.match(cleaned))

def validate_mobile_with_message(mobile: str) -> Optional[str]:
    """Return an error string if invalid, else None."""
    if not mobile or not mobile.strip():
        return "Mobile number is required."
    if not validate_mobile(mobile):
        return "Invalid mobile number. Enter a valid 10-digit Indian or international number."
    return None

def normalize_mobile(mobile: str) -> str:
    """Strip whitespace / dashes and return a clean mobile string."""
    return re.sub(r"[\s\-()]", "", mobile.strip())


# ══════════════════════════════════════════════════════════════════════════════
# Password
# ══════════════════════════════════════════════════════════════════════════════

class PasswordPolicy:
    """
    Configurable password policy.
    Defaults follow NIST SP 800-63B recommendations.
    """
    min_length:          int  = 8
    max_length:          int  = 128
    require_uppercase:   bool = True
    require_lowercase:   bool = True
    require_digit:       bool = True
    require_special:     bool = True
    special_chars:       str  = r"!@#$%^&*(),.?\":{}|<>_\-+=[]\\/;'`~"

    # Common / breached passwords to block
    COMMON_PASSWORDS: set = {
        "password", "password1", "12345678", "123456789", "qwerty123",
        "iloveyou", "admin1234", "welcome1", "monkey123", "letmein1",
        "sunshine", "princess", "football", "shadow123", "master123",
    }

_POLICY = PasswordPolicy()

def validate_password_strength(
    password: str,
    policy: PasswordPolicy = _POLICY,
) -> Optional[str]:
    """
    Validate a password against the policy rules.

    Returns:
        An error message string on failure, or None if the password is valid.
    """
    if not password:
        return "Password is required."
    if len(password) < policy.min_length:
        return f"Password must be at least {policy.min_length} characters long."
    if len(password) > policy.max_length:
        return f"Password must not exceed {policy.max_length} characters."
    if password.lower() in policy.COMMON_PASSWORDS:
        return "Password is too common. Please choose a stronger password."
    if policy.require_uppercase and not re.search(r"[A-Z]", password):
        return "Password must contain at least one uppercase letter (A–Z)."
    if policy.require_lowercase and not re.search(r"[a-z]", password):
        return "Password must contain at least one lowercase letter (a–z)."
    if policy.require_digit and not re.search(r"\d", password):
        return "Password must contain at least one digit (0–9)."
    if policy.require_special and not re.search(
        r"[" + re.escape(policy.special_chars) + r"]", password
    ):
        return "Password must contain at least one special character (!@#$%^&* etc.)."
    return None


def validate_confirm_password(password: str, confirm_password: str) -> Optional[str]:
    """
    Validate that password and confirm_password match.

    Returns:
        An error message string on mismatch, or None if they match.
    """
    if not confirm_password:
        return "Confirm password is required."
    if password != confirm_password:
        return "Passwords do not match."
    return None


def validate_new_password(
    current_password: str,
    new_password: str,
    confirm_password: str,
) -> Optional[str]:
    """
    Combined check for change-password flows:
      1. new_password != current_password
      2. new_password passes strength policy
      3. new_password == confirm_password

    Returns:
        An error message string on failure, or None on success.
    """
    if new_password == current_password:
        return "New password must be different from the current password."
    strength_error = validate_password_strength(new_password)
    if strength_error:
        return strength_error
    return validate_confirm_password(new_password, confirm_password)


# ══════════════════════════════════════════════════════════════════════════════
# Name
# ══════════════════════════════════════════════════════════════════════════════

_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z\s'\-\.]{1,99}$")

def validate_full_name(name: str) -> Optional[str]:
    """Return an error string if the name is invalid, else None."""
    name = name.strip()
    if not name:
        return "Full name is required."
    if len(name) < 2:
        return "Full name must be at least 2 characters."
    if len(name) > 100:
        return "Full name must not exceed 100 characters."
    if not _NAME_RE.match(name):
        return "Full name may only contain letters, spaces, apostrophes, hyphens, and dots."
    return None


# ══════════════════════════════════════════════════════════════════════════════
# ObjectId
# ══════════════════════════════════════════════════════════════════════════════

_OID_RE = re.compile(r"^[a-fA-F0-9]{24}$")

def validate_object_id(value: str) -> bool:
    """Return True if the string is a valid 24-char hex MongoDB ObjectId."""
    return bool(_OID_RE.match(str(value)))


# ══════════════════════════════════════════════════════════════════════════════
# URL
# ══════════════════════════════════════════════════════════════════════════════

_URL_RE = re.compile(
    r"^https?://"
    r"(?:(?:[A-Z0-9](?:[A-Z0-9\-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|localhost|\d{1,3}(?:\.\d{1,3}){3})"
    r"(?::\d+)?(?:/?|[/?]\S+)$",
    re.IGNORECASE,
)

def validate_url(url: str) -> bool:
    """Return True if the URL is well-formed (http/https)."""
    return bool(_URL_RE.match(url.strip()))


# ══════════════════════════════════════════════════════════════════════════════
# Integer / Numeric
# ══════════════════════════════════════════════════════════════════════════════

def validate_int_range(
    value,
    min_val: int = None,
    max_val: int = None,
    field_name: str = "Value",
) -> Optional[str]:
    """
    Validate that a value is an integer within [min_val, max_val].

    Returns:
        An error message on failure, or None on success.
    """
    try:
        value = int(value)
    except (TypeError, ValueError):
        return f"{field_name} must be an integer."
    if min_val is not None and value < min_val:
        return f"{field_name} must be at least {min_val}."
    if max_val is not None and value > max_val:
        return f"{field_name} must be at most {max_val}."
    return None


# ══════════════════════════════════════════════════════════════════════════════
# String length
# ══════════════════════════════════════════════════════════════════════════════

def validate_string_length(
    value: str,
    min_len: int = 0,
    max_len: int = None,
    field_name: str = "Field",
) -> Optional[str]:
    """Return error string if length is out of range, else None."""
    if not isinstance(value, str):
        return f"{field_name} must be a string."
    if len(value) < min_len:
        return f"{field_name} must be at least {min_len} character(s)."
    if max_len is not None and len(value) > max_len:
        return f"{field_name} must not exceed {max_len} character(s)."
    return None


# ══════════════════════════════════════════════════════════════════════════════
# Signup payload validator (composite)
# ══════════════════════════════════════════════════════════════════════════════

def validate_signup_payload(data: dict) -> list[str]:
    """
    Run all signup-specific validations and return a list of error messages.
    An empty list means the payload is valid.

    Checks:
      • required fields
      • full_name format
      • email format
      • mobile format
      • password strength
      • confirm_password match
    """
    errors: list[str] = []

    # 1. Required fields
    req_error = validate_required_fields(
        data, ["full_name", "email", "mobile", "password", "confirm_password"]
    )
    if req_error:
        errors.append(req_error)
        return errors   # no point checking further if fields are missing

    # 2. Full name
    name_err = validate_full_name(data["full_name"])
    if name_err:
        errors.append(name_err)

    # 3. Email
    email_err = validate_email_with_message(data["email"])
    if email_err:
        errors.append(email_err)

    # 4. Mobile
    mobile_err = validate_mobile_with_message(data["mobile"])
    if mobile_err:
        errors.append(mobile_err)

    # 5. Password strength
    pwd_err = validate_password_strength(data["password"])
    if pwd_err:
        errors.append(pwd_err)

    # 6. Confirm password (only if no strength error, avoid confusing messages)
    if not pwd_err:
        confirm_err = validate_confirm_password(data["password"], data["confirm_password"])
        if confirm_err:
            errors.append(confirm_err)

    return errors


# ══════════════════════════════════════════════════════════════════════════════
# Login payload validator (composite)
# ══════════════════════════════════════════════════════════════════════════════

def validate_login_payload(data: dict) -> list[str]:
    """
    Validate login payload. Returns list of error strings (empty = valid).
    """
    errors: list[str] = []
    req = validate_required_fields(data, ["email", "password"])
    if req:
        errors.append(req)
        return errors
    email_err = validate_email_with_message(data["email"])
    if email_err:
        errors.append(email_err)
    return errors
