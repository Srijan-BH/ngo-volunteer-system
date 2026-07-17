"""
Notification Controller
Handles notification listing, marking read, and deletion.
"""

import logging
from flask import request

from models.notification import NotificationModel
from utils.response import success_response, error_response, paginated_response
from utils.pagination import get_pagination_params

logger = logging.getLogger(__name__)


class NotificationController:

    @staticmethod
    def get_my_notifications(current_user: dict):
        """GET /api/notifications — Get notifications for authenticated user."""
        page, page_size = get_pagination_params(request)
        is_read_param = request.args.get("is_read")
        is_read = None
        if is_read_param is not None:
            is_read = is_read_param.lower() in ("true", "1")

        user_id = str(current_user["_id"])
        notifications, total = NotificationModel.find_by_user(
            user_id=user_id,
            is_read=is_read,
            page=page,
            page_size=page_size,
        )
        unread_count = NotificationModel.count_unread(user_id)
        serialized = [NotificationModel.serialize(n) for n in notifications]
        return paginated_response(
            serialized,
            total,
            page,
            page_size,
            extra={"unread_count": unread_count},
        )

    @staticmethod
    def mark_notification_read(current_user: dict, notification_id: str):
        """PATCH /api/notifications/<notification_id>/read"""
        success = NotificationModel.mark_read(notification_id)
        if not success:
            return error_response("Notification not found.", 404)
        return success_response(message="Notification marked as read.")

    @staticmethod
    def mark_all_read(current_user: dict):
        """PATCH /api/notifications/read-all"""
        count = NotificationModel.mark_all_read(str(current_user["_id"]))
        return success_response(
            message=f"{count} notification(s) marked as read.",
            data={"updated_count": count},
        )

    @staticmethod
    def delete_notification(current_user: dict, notification_id: str):
        """DELETE /api/notifications/<notification_id>"""
        success = NotificationModel.delete(notification_id)
        if not success:
            return error_response("Notification not found.", 404)
        return success_response(message="Notification deleted.")

    @staticmethod
    def get_unread_count(current_user: dict):
        """GET /api/notifications/unread-count"""
        count = NotificationModel.count_unread(str(current_user["_id"]))
        return success_response(data={"unread_count": count})
