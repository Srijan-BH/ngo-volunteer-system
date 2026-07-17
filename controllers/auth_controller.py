"""
User Auth Controller — NGO Volunteer Management System
======================================================
Handles all user-facing authentication flows:

  POST /api/auth/signup          → register new volunteer
  POST /api/auth/login           → login + JWT tokens
  POST /api/auth/logout          → revoke current access token
  POST /api/auth/refresh         → exchange refresh token for new access token
  GET  /api/auth/me              → return current user profile
  PUT  /api/auth/change-password → authenticated password change
  POST /api/auth/forgot-password → request password-reset link
  POST /api/auth/reset-password  → consume reset token + set new password

Every handler returns a standardised JSON envelope (see utils/response.py).
"""

import logging
from flask import request, current_app

from models.user            import UserModel, STATUS_ACTIVE, ROLE_VOLUNTEER
from models.password_reset  import PasswordResetModel
from models.notification    import NotificationModel, TYPE_SYSTEM
from utils.jwt_helper       import (
    generate_access_token,
    generate_refresh_token,
    generate_password_reset_token,
    verify_password_reset_token,
    decode_token,
    blacklist_token,
    is_token_blacklisted,
    _new_jti,
)
from utils.validators       import (
    validate_signup_payload,
    validate_login_payload,
    validate_required_fields,
    validate_email_with_message,
    validate_new_password,
    normalize_mobile,
)
from utils.response         import (
    success_response,
    error_response,
    validation_error_response,
    auth_success_response,
    token_response,
)

from utils.security         import sanitize_mongo_input

logger = logging.getLogger(__name__)


class AuthController:
    """User-facing authentication controller (static methods = view handlers)."""

    # ──────────────────────────────────────────────────────────────────────────
    # POST /api/auth/signup
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def signup():
        """
        Register a new volunteer account.

        Request body (JSON):
            full_name        : str  required
            email            : str  required
            mobile           : str  required
            password         : str  required
            confirm_password : str  required
            skills           : list optional
            interests        : list optional
            address          : dict optional
        """
        raw_data = request.get_json(silent=True) or {}
        data = sanitize_mongo_input(raw_data)

        # ── 1. Composite field validation ──────────────────────────────────
        errors = validate_signup_payload(data)
        if errors:
            return validation_error_response(errors)

        email  = data["email"].strip().lower()
        mobile = normalize_mobile(data["mobile"])

        # ── 2. Duplicate checks ────────────────────────────────────────────
        if UserModel.find_by_email(email):
            return error_response(
                "This email address is already registered. "
                "Try logging in or use a different email.",
                409,
                field="email",
            )
        if UserModel.find_by_mobile(mobile):
            return error_response(
                "This mobile number is already registered. "
                "Try logging in or use a different number.",
                409,
                field="mobile",
            )

        # ── 3. Create user ─────────────────────────────────────────────────
        try:
            user_id = UserModel.create({
                "full_name": data["full_name"],
                "email":     email,
                "mobile":    mobile,
                "password":  data["password"],
                "role":      ROLE_VOLUNTEER,
                "status":    STATUS_ACTIVE,
                "skills":    data.get("skills", []),
                "interests": data.get("interests", []),
                "address":   data.get("address", {}),
            })
            
            # Auto-create the volunteer profile
            from models.volunteer import VolunteerModel
            VolunteerModel.create({
                "user_id": user_id,
                "skills": data.get("skills", []),
                "interests": data.get("interests", [])
            })

            user          = UserModel.find_by_id(user_id)
            access_token  = generate_access_token(user)
            refresh_token = generate_refresh_token(user)

            # Welcome notification
            NotificationModel.create(
                user_id=user_id,
                title="Welcome to the NGO Volunteer Portal! 🎉",
                message=(
                    f"Hi {user['full_name']}, your account has been created successfully. "
                    "Start exploring events and make a difference!"
                ),
                notification_type=TYPE_SYSTEM,
            )

            logger.info(f"[SIGNUP] New user registered: {email}")
            return auth_success_response(
                entity=UserModel.serialize(user),
                access_token=access_token,
                refresh_token=refresh_token,
                message="Account created successfully. Welcome aboard!",
                status_code=201,
            )

        except ValueError as exc:
            return error_response(str(exc), 400)
        except Exception:
            logger.exception("[SIGNUP] Unexpected error")
            return error_response("Registration failed. Please try again later.", 500)

    # ──────────────────────────────────────────────────────────────────────────
    # POST /api/auth/login
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def login():
        """
        Authenticate a user and return JWT tokens.

        Request body (JSON):
            email       : str  required
            password    : str  required
            remember_me : bool optional (default false) — extends token lifetime
        """
        raw_data = request.get_json(silent=True) or {}
        data = sanitize_mongo_input(raw_data)

        # ── 1. Validate payload ────────────────────────────────────────────
        errors = validate_login_payload(data)
        if errors:
            return validation_error_response(errors)

        # ── 2. Verify credentials ──────────────────────────────────────────
        user = UserModel.verify_credentials(data["email"], data["password"])
        if not user:
            # Intentionally vague — don't reveal whether email exists
            logger.warning(f"[LOGIN] Failed attempt for: {data.get('email')}")
            return error_response("Invalid email or password.", 401)

        # ── 3. Account status checks ───────────────────────────────────────
        status = user.get("status")
        if status == "pending":
            return error_response(
                "Your account is pending approval. "
                "You will be notified once it is activated.",
                403,
            )
        if status == "suspended":
            return error_response(
                "Your account has been suspended. Please contact support.",
                403,
            )
        if status != STATUS_ACTIVE:
            return error_response(
                "Your account is inactive. Please contact support.",
                403,
            )

        # ── 4. Generate tokens ─────────────────────────────────────────────
        try:
            remember_me   = bool(data.get("remember_me", False))
            access_token  = generate_access_token(user, remember_me=remember_me)
            refresh_token = generate_refresh_token(user, remember_me=remember_me)

            UserModel.update_last_login(str(user["_id"]))

            logger.info(f"[LOGIN] User logged in: {user['email']}")
            return auth_success_response(
                entity=UserModel.serialize(user),
                access_token=access_token,
                refresh_token=refresh_token,
                message="Login successful.",
                extra={"remember_me": remember_me},
            )
        except Exception:
            logger.exception("[LOGIN] Token generation error")
            return error_response("Login failed. Please try again.", 500)

    # ──────────────────────────────────────────────────────────────────────────
    # POST /api/auth/logout
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def logout(current_user: dict):
        """
        Revoke the current access token (adds JTI to blacklist).
        Optionally also revoke the refresh token if provided.

        Request body (JSON):
            refresh_token : str  optional — if supplied, also revoked
        """
        auth   = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return error_response("No active session found.", 400)

        access_token = auth.split(" ", 1)[1].strip()

        try:
            blacklist_token(access_token)

            # Also revoke refresh token if the client sends it
            data = request.get_json(silent=True) or {}
            if rt := data.get("refresh_token"):
                if not is_token_blacklisted(rt):
                    blacklist_token(rt)

            logger.info(f"[LOGOUT] User logged out: {current_user.get('email')}")
            return success_response(message="Logged out successfully. See you soon!")
        except Exception:
            logger.exception("[LOGOUT] Error")
            return error_response("Logout failed. Please try again.", 500)

    # ──────────────────────────────────────────────────────────────────────────
    # POST /api/auth/refresh
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def refresh_token():
        """
        Exchange a valid refresh token for a new access token.

        Request body (JSON):
            refresh_token : str  required
        """
        data = request.get_json(silent=True) or {}
        rt   = data.get("refresh_token", "").strip()

        if not rt:
            return error_response("refresh_token is required.", 400)

        # ── 1. Check blacklist first (fast path) ───────────────────────────
        if is_token_blacklisted(rt):
            return error_response(
                "Refresh token has been revoked. Please log in again.", 401
            )

        # ── 2. Decode & validate ───────────────────────────────────────────
        payload = decode_token(rt)
        if not payload:
            return error_response(
                "Invalid or expired refresh token. Please log in again.", 401
            )
        if payload.get("type") != "refresh":
            return error_response("Token type mismatch. Provide a refresh token.", 401)
        if payload.get("entity") != "user":
            return error_response("Invalid token entity.", 401)

        # ── 3. Load user ───────────────────────────────────────────────────
        user = UserModel.find_by_id(payload.get("sub"))
        if not user:
            return error_response("User account not found.", 401)
        if user.get("status") != STATUS_ACTIVE:
            return error_response("Account is no longer active.", 403)

        # ── 4. Issue new access token ──────────────────────────────────────
        new_access = generate_access_token(user)
        logger.debug(f"[REFRESH] Token refreshed for: {user['email']}")
        return token_response(new_access, message="Access token refreshed successfully.")

    # ──────────────────────────────────────────────────────────────────────────
    # GET /api/auth/me
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def me(current_user: dict):
        """Return the authenticated user's profile."""
        return success_response(
            data={"user": UserModel.serialize(current_user)},
            message="Profile retrieved successfully.",
        )

    # ──────────────────────────────────────────────────────────────────────────
    # PUT /api/auth/me
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def update_profile(current_user: dict):
        """Update authenticated user's profile details."""
        raw_data = request.get_json(silent=True) or {}
        data = sanitize_mongo_input(raw_data)
        
        allowed_fields = {"full_name", "mobile", "skills", "interests", "address", "location"}
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        
        if not update_data:
            return error_response("No valid fields provided for update.", 400)
            
        if "full_name" in update_data:
            err = __import__("utils.validators", fromlist=["validate_full_name"]).validate_full_name(update_data["full_name"])
            if err:
                return error_response(err, 400, field="full_name")
                
        user_id = str(current_user["_id"])
        
        # 1. Update the User Model
        user_update = {k: v for k, v in update_data.items() if k in {"full_name", "mobile", "skills", "interests", "address"}}
        
        # Sync location to user address
        if "location" in update_data:
            addr = current_user.get("address") or {}
            addr["city"] = update_data["location"]
            user_update["address"] = addr
            
        if user_update:
            success = UserModel.update(user_id, user_update)
            if not success:
                return error_response("Failed to update profile.", 500)
        
        # 2. Update the Volunteer Model
        from models.volunteer import VolunteerModel
        volunteer = VolunteerModel.find_by_user_id(user_id)
        if volunteer:
            vol_update = {}
            if "skills" in update_data:
                vol_update["skills"] = update_data["skills"]
            if "interests" in update_data:
                vol_update["interests"] = update_data["interests"]
            if "location" in update_data:
                vol_update["location"] = update_data["location"]
            
            if vol_update:
                from database.connection import get_collection
                from bson import ObjectId
                get_collection("volunteers").update_one(
                    {"_id": ObjectId(volunteer["_id"])}, 
                    {"$set": vol_update}
                )
            
        updated_user = UserModel.find_by_id(user_id)
        return success_response(
            data={"user": UserModel.serialize(updated_user)}, 
            message="Profile updated successfully."
        )

    # ──────────────────────────────────────────────────────────────────────────
    # POST /api/auth/me/avatar
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def upload_avatar(current_user: dict):
        """Upload and set avatar for authenticated user."""
        if 'avatar' not in request.files:
            return error_response("No file uploaded.", 400)
            
        file = request.files['avatar']
        if file.filename == '':
            return error_response("No selected file.", 400)
            
        from utils.file_upload import save_upload
        result = save_upload(file, upload_type="profile")
        
        if not result["success"]:
            return error_response(result["error"], 400)
            
        user_id = str(current_user["_id"])
        success = UserModel.update(user_id, {"avatar_url": result["url"]})
        
        if not success:
            return error_response("Failed to update user record with new avatar.", 500)
            
        return success_response(
            data={"avatar_url": result["url"]}, 
            message="Avatar uploaded successfully."
        )

    # ──────────────────────────────────────────────────────────────────────────
    # PUT /api/auth/change-password
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def change_password(current_user: dict):
        """
        Change the authenticated user's password.

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

        # ── 1. Verify current password ─────────────────────────────────────
        user = UserModel.verify_credentials(current_user["email"], data["current_password"])
        if not user:
            return error_response("Current password is incorrect.", 401, field="current_password")

        # ── 2. Validate new password ───────────────────────────────────────
        pwd_error = validate_new_password(
            data["current_password"],
            data["new_password"],
            data["confirm_password"],
        )
        if pwd_error:
            return error_response(pwd_error, 422, field="new_password")

        # ── 3. Persist ─────────────────────────────────────────────────────
        ok = UserModel.update_password(str(current_user["_id"]), data["new_password"])
        if not ok:
            return error_response("Failed to update password. Please try again.", 500)

        logger.info(f"[CHANGE-PWD] Password changed for: {current_user['email']}")
        return success_response(message="Password changed successfully.")

    # ──────────────────────────────────────────────────────────────────────────
    # POST /api/auth/forgot-password
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def forgot_password():
        """
        Initiate a password-reset flow.
        Generates a 15-minute reset token and (in production) emails it to the user.

        Request body (JSON):
            email : str  required

        Security note: Returns the same response whether the email exists or not
        to prevent user enumeration attacks.
        """
        data = request.get_json(silent=True) or {}

        email_err = validate_email_with_message(data.get("email", ""))
        if email_err:
            return error_response(email_err, 400, field="email")

        email = data["email"].strip().lower()
        SAFE_MSG = (
            "If that email is registered, you will receive a password-reset link shortly. "
            "Please check your inbox (and spam folder)."
        )

        user = UserModel.find_by_email(email)
        if not user:
            # Return safe response — do NOT reveal non-existence
            logger.info(f"[FORGOT-PWD] Email not found (silent): {email}")
            return success_response(message=SAFE_MSG)

        if user.get("status") != STATUS_ACTIVE:
            # Return safe response — do NOT reveal account status
            logger.info(f"[FORGOT-PWD] Inactive account (silent): {email}")
            return success_response(message=SAFE_MSG)

        try:
            user_id      = str(user["_id"])
            reset_token  = generate_password_reset_token(user_id, entity="user")

            # Decode to get JTI (needed for storage)
            payload = decode_token(reset_token)
            jti     = payload.get("jti", "")

            # Store hashed token record (invalidates any prior requests)
            PasswordResetModel.create(user_id, "user", reset_token, jti)

            # ── In production: send via email ──────────────────────────────
            # reset_url = f"{current_app.config.get('FRONTEND_URL')}/reset-password?token={reset_token}"
            # send_reset_email(user["email"], user["full_name"], reset_url)

            logger.info(f"[FORGOT-PWD] Reset token generated for: {email}")

            # ── In development: return token directly ──────────────────────
            if current_app.config.get("DEBUG"):
                return success_response(
                    data={"reset_token": reset_token},     # Remove in production!
                    message=SAFE_MSG,
                )
            return success_response(message=SAFE_MSG)

        except Exception:
            logger.exception("[FORGOT-PWD] Error generating reset token")
            return success_response(message=SAFE_MSG)      # Never reveal the error

    # ──────────────────────────────────────────────────────────────────────────
    # POST /api/auth/reset-password
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def reset_password():
        """
        Consume a password-reset token and set a new password.

        Request body (JSON):
            token            : str  required  (the JWT from forgot-password)
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

        # ── 1. Verify the reset JWT ────────────────────────────────────────
        payload = verify_password_reset_token(raw_token)
        if not payload:
            return error_response(
                "Invalid or expired reset token. Please request a new one.", 400
            )

        jti     = payload.get("jti", "")
        user_id = payload.get("sub")

        # ── 2. Validate the stored record ──────────────────────────────────
        if not PasswordResetModel.is_valid(jti, raw_token):
            return error_response(
                "Reset token is invalid, expired, or has already been used.", 400
            )

        # ── 3. Load user ───────────────────────────────────────────────────
        user = UserModel.find_by_id(user_id)
        if not user or user.get("status") != STATUS_ACTIVE:
            return error_response("User account not found or inactive.", 400)

        # ── 4. Validate new password ───────────────────────────────────────
        pwd_error = validate_new_password(
            "",                          # No "current" to compare against
            data["new_password"],
            data["confirm_password"],
        )
        if pwd_error and "different from the current" not in pwd_error:
            # Skip the "must differ from current" check (we don't have the plaintext)
            return error_response(pwd_error, 422, field="new_password")

        strength_err = __import__(
            "utils.validators", fromlist=["validate_password_strength"]
        ).validate_password_strength(data["new_password"])
        if strength_err:
            return error_response(strength_err, 422, field="new_password")

        from utils.validators import validate_confirm_password
        confirm_err = validate_confirm_password(data["new_password"], data["confirm_password"])
        if confirm_err:
            return error_response(confirm_err, 422, field="confirm_password")

        # ── 5. Persist & clean up ──────────────────────────────────────────
        try:
            UserModel.update_password(user_id, data["new_password"])
            PasswordResetModel.consume(jti)
            blacklist_token(raw_token)      # Single-use: revoke the JWT

            NotificationModel.create(
                user_id=user_id,
                title="Password Reset Successful",
                message=(
                    "Your password was reset successfully. "
                    "If you did not perform this action, contact support immediately."
                ),
                notification_type=TYPE_SYSTEM,
            )

            logger.info(f"[RESET-PWD] Password reset successful for user_id={user_id}")
            return success_response(
                message="Password reset successfully. You can now log in with your new password."
            )
        except Exception:
            logger.exception("[RESET-PWD] Error resetting password")
            return error_response("Failed to reset password. Please try again.", 500)
