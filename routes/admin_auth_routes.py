"""
Admin Auth Routes — Blueprint
/api/admin/auth/...

Endpoint map:
  POST   /api/admin/auth/login           → AdminAuthController.login           (public)
  POST   /api/admin/auth/logout          → AdminAuthController.logout          (admin auth)
  POST   /api/admin/auth/refresh         → AdminAuthController.refresh_token   (public)
  GET    /api/admin/auth/me              → AdminAuthController.me              (admin auth)
  PUT    /api/admin/auth/change-password → AdminAuthController.change_password (admin auth)
  POST   /api/admin/auth/forgot-password → AdminAuthController.forgot_password (public)
  POST   /api/admin/auth/reset-password  → AdminAuthController.reset_password  (public)
"""

from flask import Blueprint

from controllers.admin_auth_controller import AdminAuthController
from middleware.auth_middleware         import require_admin_auth

admin_auth_bp = Blueprint("admin_auth", __name__)

# ── Public endpoints ──────────────────────────────────────────────────────────

@admin_auth_bp.route("/login", methods=["POST"])
def admin_login():
    """Authenticate an admin and return JWT tokens."""
    return AdminAuthController.login()


@admin_auth_bp.route("/refresh", methods=["POST"])
def admin_refresh_token():
    """Exchange a valid admin refresh token for a new access token."""
    return AdminAuthController.refresh_token()


@admin_auth_bp.route("/forgot-password", methods=["POST"])
def admin_forgot_password():
    """Request an admin password-reset link."""
    return AdminAuthController.forgot_password()


@admin_auth_bp.route("/reset-password", methods=["POST"])
def admin_reset_password():
    """Consume a one-time reset token and set a new admin password."""
    return AdminAuthController.reset_password()


# ── Protected endpoints (require valid admin JWT) ─────────────────────────────

@admin_auth_bp.route("/logout", methods=["POST"])
@require_admin_auth
def admin_logout(current_admin):
    """Revoke the current admin access token."""
    return AdminAuthController.logout(current_admin)


@admin_auth_bp.route("/me", methods=["GET"])
@require_admin_auth
def admin_me(current_admin):
    """Return the authenticated admin's profile."""
    return AdminAuthController.me(current_admin)


@admin_auth_bp.route("/change-password", methods=["PUT"])
@require_admin_auth
def admin_change_password(current_admin):
    """Change password for the authenticated admin."""
    return AdminAuthController.change_password(current_admin)
