"""
User Auth Routes — Blueprint
/api/auth/...

Endpoint map:
  POST   /api/auth/signup           → AuthController.signup          (public)
  POST   /api/auth/login            → AuthController.login           (public)
  POST   /api/auth/logout           → AuthController.logout          (protected)
  POST   /api/auth/refresh          → AuthController.refresh_token   (public)
  GET    /api/auth/me               → AuthController.me              (protected)
  PUT    /api/auth/change-password  → AuthController.change_password (protected)
  POST   /api/auth/forgot-password  → AuthController.forgot_password (public)
  POST   /api/auth/reset-password   → AuthController.reset_password  (public)
"""

from flask import Blueprint

from controllers.auth_controller import AuthController
from middleware.auth_middleware   import require_user_auth

auth_bp = Blueprint("auth", __name__)

# ── Public endpoints ──────────────────────────────────────────────────────────

@auth_bp.route("/signup", methods=["POST"])
def signup():
    """Register a new volunteer account."""
    return AuthController.signup()


@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate a user and return JWT access + refresh tokens."""
    return AuthController.login()


@auth_bp.route("/refresh", methods=["POST"])
def refresh_token():
    """Exchange a valid refresh token for a new access token."""
    return AuthController.refresh_token()


@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    """Request a password-reset link (sent to registered email)."""
    return AuthController.forgot_password()


@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    """Consume a one-time reset token and set a new password."""
    return AuthController.reset_password()


# ── Protected endpoints (require valid user JWT) ──────────────────────────────

@auth_bp.route("/logout", methods=["POST"])
@require_user_auth
def logout(current_user):
    """Revoke the current access (and optionally refresh) token."""
    return AuthController.logout(current_user)


@auth_bp.route("/me", methods=["GET"])
@require_user_auth
def me(current_user):
    """Return the authenticated user's profile."""
    return AuthController.me(current_user)


@auth_bp.route("/me", methods=["PUT"])
@require_user_auth
def update_profile(current_user):
    """Update the authenticated user's profile."""
    return AuthController.update_profile(current_user)


@auth_bp.route("/me/avatar", methods=["POST"])
@require_user_auth
def upload_avatar(current_user):
    """Upload a new avatar for the authenticated user."""
    return AuthController.upload_avatar(current_user)


@auth_bp.route("/change-password", methods=["PUT"])
@require_user_auth
def change_password(current_user):
    """Change password for the authenticated user."""
    return AuthController.change_password(current_user)
