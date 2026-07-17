"""Notification Routes — Blueprint"""

from flask import Blueprint
from controllers.notification_controller import NotificationController
from middleware.auth_middleware import require_auth

notification_bp = Blueprint("notifications", __name__)


@notification_bp.route("", methods=["GET"])
@notification_bp.route("/", methods=["GET"])
@require_auth
def get_my_notifications(current_user):
    return NotificationController.get_my_notifications(current_user)


@notification_bp.route("/unread-count", methods=["GET"])
@require_auth
def get_unread_count(current_user):
    return NotificationController.get_unread_count(current_user)


@notification_bp.route("/read-all", methods=["PATCH"])
@require_auth
def mark_all_read(current_user):
    return NotificationController.mark_all_read(current_user)


@notification_bp.route("/<notification_id>/read", methods=["PATCH"])
@require_auth
def mark_notification_read(current_user, notification_id):
    return NotificationController.mark_notification_read(current_user, notification_id)


@notification_bp.route("/<notification_id>", methods=["DELETE"])
@require_auth
def delete_notification(current_user, notification_id):
    return NotificationController.delete_notification(current_user, notification_id)
