"""
User Routes — Blueprint
Admin-facing user management endpoints.
"""

from flask import Blueprint
from controllers.user_controller import UserController
from middleware.auth_middleware import require_auth, require_role

user_bp = Blueprint("users", __name__)


@user_bp.route("/", methods=["GET"])
@require_auth
@require_role("admin")
def get_all_users(current_user):
    return UserController.get_all_users(current_user)


@user_bp.route("/<user_id>", methods=["GET"])
@require_auth
@require_role("admin", "staff")
def get_user(current_user, user_id):
    return UserController.get_user(current_user, user_id)


@user_bp.route("/<user_id>", methods=["PUT"])
@require_auth
@require_role("admin")
def update_user(current_user, user_id):
    return UserController.update_user(current_user, user_id)


@user_bp.route("/<user_id>", methods=["DELETE"])
@require_auth
@require_role("admin")
def delete_user(current_user, user_id):
    return UserController.delete_user(current_user, user_id)


@user_bp.route("/<user_id>/activate", methods=["PATCH"])
@require_auth
@require_role("admin")
def activate_user(current_user, user_id):
    return UserController.activate_user(current_user, user_id)
