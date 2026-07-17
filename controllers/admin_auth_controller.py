"""
Admin Auth Controller — NGO Volunteer Management System
=======================================================
Handles all admin-facing authentication flows:

  POST /api/admin/auth/login           → admin login + JWT tokens
  POST /api/admin/auth/logout          → revoke current admin token
  POST /api/admin/auth/refresh         → exchange refresh token for new access token
  GET  /api/admin/auth/me              → return current admin profile
  PUT  /api/admin/auth/change-password → admin password change
  POST /api/admin/auth/forgot-password → request admin password-reset link
  POST /api/admin/auth/reset-password  → consume reset token + set new password

Admin tokens use entity="admin" in the JWT payload, which routes them
through AdminModel instead of UserModel in all middleware checks.
"""

import logging
from flask import request, current_app

from models.admin           import AdminModel, ROLE_SUPER_ADMIN
from models.password_reset  import PasswordResetModel
from utils.jwt_helper       import (
    generate_admin_access_token,
    generate_admin_refresh_token,
    generate_password_reset_token,
    verify_password_reset_token,
    decode_token,
    blacklist_token,
    is_token_blacklisted,
)
from utils.validators       import (
    validate_login_payload,
    validate_required_fields,
    validate_email_with_message,
    validate_password_strength,
    validate_confirm_password,
    validate_new_password,
)
from utils.response         import (
    success_response,
    error_response,
    validation_error_response,
    auth_success_response,
    token_response,
)

logger = logging.getLogger(__name__)


class AdminAuthController:
    """Admin-facing authentication controller (static methods = view handlers)."""

    # ──────────────────────────────────────────────────────────────────────────
    # POST /api/admin/auth/login
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def login():
        """
        Authenticate an admin and return JWT tokens.

        Request body (JSON):
            email       : str   required
            password    : str   required
            remember_me : bool  optional (default false) — max 7-day token
        """
        data = request.get_json(silent=True) or {}

        # ── 1. Validate payload ────────────────────────────────────────────
        errors = validate_login_payload(data)
        if errors:
            return validation_error_response(errors)

        # ── 2. Verify credentials ──────────────────────────────────────────
        admin = AdminModel.verify_credentials(data["email"], data["password"])
        if not admin:
            logger.warning(f"[ADMIN-LOGIN] Failed attempt for: {data.get('email')}")
            return error_response("Invalid email or password.", 401)

        # ── 3. Account status check ────────────────────────────────────────
        if not admin.get("is_active"):
            return error_response(
                "This admin account has been deactivated. "
                "Please contact a super admin.",
                403,
            )

        # ── 4. Generate admin tokens ───────────────────────────────────────
        try:
            remember_me   = bool(data.get("remember_me", False))
            access_token  = generate_admin_access_token(admin, remember_me=remember_me)
            refresh_token = generate_admin_refresh_token(admin)

            AdminModel.update_last_login(str(admin["_id"]))

            logger.info(f"[ADMIN-LOGIN] Admin logged in: {admin['email']} role={admin['role']}")
            return auth_success_response(
                entity=AdminModel.serialize(admin),
                access_token=access_token,
                refresh_token=refresh_token,
                message="Admin login successful.",
                extra={
                    "role":        admin["role"],
                    "remember_me": remember_me,
                },
            )
        except Exception:
            logger.exception("[ADMIN-LOGIN] Token generation error")
            return error_response("Login failed. Please try again.", 500)

    # ──────────────────────────────────────────────────────────────────────────
    # POST /api/admin/auth/logout
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def logout(current_admin: dict):
        """
        Revoke the admin's current access token.

        Request body (JSON):
            refresh_token : str  optional — if supplied, also revoked
        """
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return error_response("No active admin session found.", 400)

        access_token = auth.split(" ", 1)[1].strip()

        try:
            blacklist_token(access_token)

            data = request.get_json(silent=True) or {}
            if rt := data.get("refresh_token"):
                if not is_token_blacklisted(rt):
                    blacklist_token(rt)

            logger.info(f"[ADMIN-LOGOUT] Admin logged out: {current_admin.get('email')}")
            return success_response(message="Admin logged out successfully.")
        except Exception:
            logger.exception("[ADMIN-LOGOUT] Error")
            return error_response("Logout failed. Please try again.", 500)

    # ──────────────────────────────────────────────────────────────────────────
    # POST /api/admin/auth/refresh
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def refresh_token():
        """
        Exchange a valid admin refresh token for a new access token.

        Request body (JSON):
            refresh_token : str  required
        """
        data = request.get_json(silent=True) or {}
        rt   = data.get("refresh_token", "").strip()

        if not rt:
            return error_response("refresh_token is required.", 400)

        if is_token_blacklisted(rt):
            return error_response("Refresh token has been revoked. Please log in again.", 401)

        payload = decode_token(rt)
        if not payload:
            return error_response("Invalid or expired refresh token.", 401)
        if payload.get("type") != "refresh":
            return error_response("Token type mismatch. Provide a refresh token.", 401)
        if payload.get("entity") != "admin":
            return error_response("This token does not belong to an admin account.", 401)

        admin = AdminModel.find_by_id(payload.get("sub"))
        if not admin:
            return error_response("Admin account not found.", 401)
        if not admin.get("is_active"):
            return error_response("Admin account is no longer active.", 403)

        new_access = generate_admin_access_token(admin)
        logger.debug(f"[ADMIN-REFRESH] Token refreshed for: {admin['email']}")
        return token_response(new_access, message="Admin access token refreshed.")

    # ──────────────────────────────────────────────────────────────────────────
    # GET /api/admin/auth/me
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def me(current_admin: dict):
        """Return the current admin's profile."""
        return success_response(
            data={"admin": AdminModel.serialize(current_admin)},
            message="Admin profile retrieved.",
        )

    # ──────────────────────────────────────────────────────────────────────────
    # PUT /api/admin/auth/change-password
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def change_password(current_admin: dict):
        """
        Change the authenticated admin's password.

        Request body (JSON):
            current_password : str  required
            new_password     : str  required
            confirm_password : str  required
        """
        data = request.get_json(silent=True) or {}

        field_error = validate_required_fields(
            data, ["current_password", "new_password", "confirm_password"]
        )
        if field_error:
            return error_response(field_error, 400)

        admin = AdminModel.verify_credentials(current_admin["email"], data["current_password"])
        if not admin:
            return error_response("Current password is incorrect.", 401, field="current_password")

        pwd_error = validate_new_password(
            data["current_password"],
            data["new_password"],
            data["confirm_password"],
        )
        if pwd_error:
            return error_response(pwd_error, 422, field="new_password")

        ok = AdminModel.update_password(str(current_admin["_id"]), data["new_password"])
        if not ok:
            return error_response("Failed to update password.", 500)

        logger.info(f"[ADMIN-CHANGE-PWD] Password changed for: {current_admin['email']}")
        return success_response(message="Admin password changed successfully.")

    # ──────────────────────────────────────────────────────────────────────────
    # POST /api/admin/auth/forgot-password
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def forgot_password():
        """
        Initiate an admin password-reset flow.

        Request body (JSON):
            email : str  required
        """
        data = request.get_json(silent=True) or {}

        email_err = validate_email_with_message(data.get("email", ""))
        if email_err:
            return error_response(email_err, 400, field="email")

        email    = data["email"].strip().lower()
        SAFE_MSG = (
            "If that admin email is registered, a reset link will be sent. "
            "Please check your inbox."
        )

        admin = AdminModel.find_by_email(email)
        if not admin or not admin.get("is_active"):
            logger.info(f"[ADMIN-FORGOT-PWD] Email not found or inactive (silent): {email}")
            return success_response(message=SAFE_MSG)

        try:
            admin_id    = str(admin["_id"])
            reset_token = generate_password_reset_token(admin_id, entity="admin")
            payload     = decode_token(reset_token)
            jti         = payload.get("jti", "")

            PasswordResetModel.create(admin_id, "admin", reset_token, jti)

            logger.info(f"[ADMIN-FORGOT-PWD] Reset token generated for: {email}")

            if current_app.config.get("DEBUG"):
                return success_response(
                    data={"reset_token": reset_token},
                    message=SAFE_MSG,
                )
            return success_response(message=SAFE_MSG)

        except Exception:
            logger.exception("[ADMIN-FORGOT-PWD] Error")
            return success_response(message=SAFE_MSG)

    # ──────────────────────────────────────────────────────────────────────────
    # POST /api/admin/auth/reset-password
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def reset_password():
        """
        Consume an admin password-reset token and set a new password.

        Request body (JSON):
            token            : str  required
            new_password     : str  required
            confirm_password : str  required
        """
        data = request.get_json(silent=True) or {}

        field_error = validate_required_fields(
            data, ["token", "new_password", "confirm_password"]
        )
        if field_error:
            return error_response(field_error, 400)

        raw_token = data["token"].strip()

        payload = verify_password_reset_token(raw_token)
        if not payload or payload.get("entity") != "admin":
            return error_response("Invalid or expired admin reset token.", 400)

        jti      = payload.get("jti", "")
        admin_id = payload.get("sub")

        if not PasswordResetModel.is_valid(jti, raw_token):
            return error_response(
                "Reset token is invalid, expired, or already used.", 400
            )

        admin = AdminModel.find_by_id(admin_id)
        if not admin or not admin.get("is_active"):
            return error_response("Admin account not found or inactive.", 400)

        strength_err = validate_password_strength(data["new_password"])
        if strength_err:
            return error_response(strength_err, 422, field="new_password")

        confirm_err = validate_confirm_password(data["new_password"], data["confirm_password"])
        if confirm_err:
            return error_response(confirm_err, 422, field="confirm_password")

        try:
            AdminModel.update_password(admin_id, data["new_password"])
            PasswordResetModel.consume(jti)
            blacklist_token(raw_token)

            logger.info(f"[ADMIN-RESET-PWD] Password reset for admin_id={admin_id}")
            return success_response(
                message="Admin password reset successfully. Please log in with your new password."
            )
        except Exception:
            logger.exception("[ADMIN-RESET-PWD] Error")
            return error_response("Failed to reset password.", 500)
