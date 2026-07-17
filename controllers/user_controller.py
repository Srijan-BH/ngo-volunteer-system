"""
User Controller
Admin-facing user management: list, get, update role, activate/deactivate, delete.
"""

import logging
from flask import request

from models.user import UserModel
from utils.validators import validate_email
from utils.response import success_response, error_response, paginated_response
from utils.pagination import get_pagination_params

logger = logging.getLogger(__name__)


class UserController:

    @staticmethod
    def get_all_users(current_user: dict):
        """GET /api/users — Admin: list all users with pagination & filters."""
        page, page_size = get_pagination_params(request)
        role = request.args.get("role")
        is_active = request.args.get("is_active")
        search = request.args.get("search")

        filters = {}
        if role:
            filters["role"] = role
        if is_active is not None:
            filters["is_active"] = is_active.lower() in ("true", "1")
        if search:
            filters["$or"] = [
                {"email": {"$regex": search, "$options": "i"}},
                {"username": {"$regex": search, "$options": "i"}},
                {"first_name": {"$regex": search, "$options": "i"}},
                {"last_name": {"$regex": search, "$options": "i"}},
            ]

        users, total = UserModel.find_all(filters=filters, page=page, page_size=page_size)
        serialized = [UserModel.serialize(u) for u in users]
        return paginated_response(serialized, total, page, page_size)

    @staticmethod
    def get_user(current_user: dict, user_id: str):
        """GET /api/users/<user_id>"""
        user = UserModel.find_by_id(user_id)
        if not user:
            return error_response("User not found.", 404)
        return success_response(data={"user": UserModel.serialize(user)})

    @staticmethod
    def update_user(current_user: dict, user_id: str):
        """PUT /api/users/<user_id> — Admin: update user fields."""
        data = request.get_json(silent=True) or {}
        if not data:
            return error_response("No data provided.", 400)

        # Whitelist updatable fields
        allowed = {"first_name", "last_name", "phone", "role", "is_active", "email_verified"}
        update = {k: v for k, v in data.items() if k in allowed}

        if "email" in data:
            if not validate_email(data["email"]):
                return error_response("Invalid email.", 400)
            update["email"] = data["email"].strip().lower()

        if not update:
            return error_response("No valid fields to update.", 400)

        success = UserModel.update(user_id, update)
        if not success:
            return error_response("User not found or no changes made.", 404)

        user = UserModel.find_by_id(user_id)
        return success_response(data={"user": UserModel.serialize(user)}, message="User updated successfully.")

    @staticmethod
    def delete_user(current_user: dict, user_id: str):
        """DELETE /api/users/<user_id> — Admin: soft delete user."""
        if str(current_user["_id"]) == user_id:
            return error_response("Cannot delete your own account.", 400)

        success = UserModel.soft_delete(user_id)
        if not success:
            return error_response("User not found.", 404)
        return success_response(message="User deactivated successfully.")

    @staticmethod
    def activate_user(current_user: dict, user_id: str):
        """PATCH /api/users/<user_id>/activate — Admin: reactivate a user."""
        success = UserModel.update(user_id, {"is_active": True})
        if not success:
            return error_response("User not found.", 404)
        return success_response(message="User activated successfully.")
