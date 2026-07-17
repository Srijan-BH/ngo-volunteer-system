"""Dashboard Routes — Blueprint"""

from flask import Blueprint
from controllers.dashboard_controller import DashboardController
from middleware.auth_middleware import require_auth, require_admin_auth

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/overview", methods=["GET"])
@require_admin_auth
def get_overview(current_admin):
    return DashboardController.get_overview(current_admin)


@dashboard_bp.route("/sidebar-stats", methods=["GET"])
@require_admin_auth
def get_sidebar_stats(current_admin):
    return DashboardController.get_sidebar_stats(current_admin)


@dashboard_bp.route("/event-trends", methods=["GET"])
@require_admin_auth
def get_event_trends(current_admin):
    return DashboardController.get_event_trends(current_admin)


@dashboard_bp.route("/skills", methods=["GET"])
@require_admin_auth
def get_volunteer_by_skills(current_admin):
    return DashboardController.get_volunteer_by_skills(current_admin)


@dashboard_bp.route("/categories", methods=["GET"])
@require_admin_auth
def get_category_breakdown(current_admin):
    return DashboardController.get_category_breakdown(current_admin)


@dashboard_bp.route("/volunteer", methods=["GET"])
@require_auth
def get_volunteer_overview(current_user):
    return DashboardController.get_volunteer_overview(current_user)

