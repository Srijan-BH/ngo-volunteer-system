"""
Event Routes — Blueprint
"""

from flask import Blueprint
from controllers.event_controller import EventController
from middleware.auth_middleware import require_auth, require_role, optional_auth, require_staff_or_admin

event_bp = Blueprint("events", __name__)


@event_bp.route("/", methods=["GET"])
@optional_auth
def get_all_events(current_user):
    return EventController.get_all_events(current_user)


@event_bp.route("/search", methods=["GET"])
@optional_auth
def search_events(current_user):
    return EventController.search_events(current_user)


@event_bp.route("/<event_id>", methods=["GET"])
@optional_auth
def get_event(current_user, event_id):
    return EventController.get_event(event_id, current_user)


@event_bp.route("/", methods=["POST"])
@require_staff_or_admin
def create_event(current_user):
    return EventController.create_event(current_user)


@event_bp.route("/<event_id>", methods=["PUT"])
@require_staff_or_admin
def update_event(current_user, event_id):
    return EventController.update_event(current_user, event_id)


@event_bp.route("/<event_id>", methods=["DELETE"])
@require_staff_or_admin
def delete_event(current_user, event_id):
    return EventController.delete_event(current_user, event_id)


@event_bp.route("/<event_id>/feedback", methods=["GET"])
@require_staff_or_admin
def get_event_feedback(current_user, event_id):
    return EventController.get_event_feedback(current_user, event_id)


@event_bp.route("/<event_id>/status", methods=["PATCH"])
@require_staff_or_admin
def update_event_status(current_user, event_id):
    return EventController.update_event_status(current_user, event_id)


@event_bp.route("/<event_id>/register", methods=["POST"])
@require_auth
def register_for_event(current_user, event_id):
    return EventController.register_for_event(current_user, event_id)


@event_bp.route("/<event_id>/register", methods=["DELETE"])
@require_auth
def cancel_registration(current_user, event_id):
    return EventController.cancel_registration(current_user, event_id)


@event_bp.route("/<event_id>/registrations", methods=["GET"])
@require_staff_or_admin
def get_event_registrations(current_user, event_id):
    return EventController.get_event_registrations(current_user, event_id)


@event_bp.route("/<event_id>/image", methods=["POST"])
@require_staff_or_admin
def upload_event_image(current_user, event_id):
    return EventController.upload_event_image(current_user, event_id)
