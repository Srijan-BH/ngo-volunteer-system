"""
Volunteer Routes — Blueprint
"""

from flask import Blueprint
from controllers.volunteer_controller import VolunteerController
from middleware.auth_middleware import require_auth, require_role, require_admin_auth, require_staff_or_admin

volunteer_bp = Blueprint("volunteers", __name__)


@volunteer_bp.route("/", methods=["GET"])
@require_staff_or_admin
def get_all_volunteers(current_user):
    return VolunteerController.get_all_volunteers(current_user)


@volunteer_bp.route("/stats", methods=["GET"])
@require_admin_auth
def get_volunteer_stats(current_user):
    return VolunteerController.get_volunteer_stats(current_user)


@volunteer_bp.route("/export", methods=["GET"])
@require_admin_auth
def export_volunteers(current_user):
    return VolunteerController.export_volunteers(current_user)


@volunteer_bp.route("/me", methods=["GET"])
@require_auth
def get_my_profile(current_user):
    return VolunteerController.get_my_profile(current_user)


@volunteer_bp.route("/me", methods=["PUT"])
@require_auth
def update_my_profile(current_user):
    return VolunteerController.update_my_profile(current_user)


@volunteer_bp.route("/me/picture", methods=["POST"])
@require_auth
def upload_profile_picture(current_user):
    return VolunteerController.upload_profile_picture(current_user)


@volunteer_bp.route("/<volunteer_id>", methods=["GET"])
@require_staff_or_admin
def get_volunteer(current_user, volunteer_id):
    return VolunteerController.get_volunteer(current_user, volunteer_id)


@volunteer_bp.route("/<volunteer_id>/status", methods=["PATCH"])
@require_staff_or_admin
def update_volunteer_status(current_user, volunteer_id):
    return VolunteerController.update_volunteer_status(current_user, volunteer_id)

