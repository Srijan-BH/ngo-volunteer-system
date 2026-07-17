"""
Models Package — NGO Volunteer Management System

Exports all model classes and their constants for convenient importing:

    from models import UserModel, AdminModel, EventModel
    from models import CategoryModel, JoinRequestModel, NotificationModel
"""

from models.user          import UserModel, ROLE_VOLUNTEER, ROLE_STAFF, ROLE_ADMIN, VALID_ROLES
from models.admin         import AdminModel, ROLE_SUPER_ADMIN, ROLE_MODERATOR
from models.category      import CategoryModel
from models.event         import EventModel, STATUS_DRAFT, STATUS_PUBLISHED, STATUS_COMPLETED, STATUS_CANCELLED
from models.join_request  import JoinRequestModel, STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED, STATUS_ATTENDED
from models.notification  import (
    NotificationModel,
    TYPE_JOIN_REQUEST, TYPE_APPROVAL, TYPE_REJECTION,
    TYPE_EVENT_REMINDER, TYPE_EVENT_UPDATE, TYPE_EVENT_CANCELLED,
    TYPE_ANNOUNCEMENT, TYPE_SYSTEM, TYPE_GENERAL,
)

__all__ = [
    # ── Models
    "UserModel",
    "AdminModel",
    "CategoryModel",
    "EventModel",
    "JoinRequestModel",
    "NotificationModel",
    # ── User constants
    "ROLE_VOLUNTEER", "ROLE_STAFF", "ROLE_ADMIN", "VALID_ROLES",
    # ── Admin constants
    "ROLE_SUPER_ADMIN", "ROLE_MODERATOR",
    # ── Event status
    "STATUS_DRAFT", "STATUS_PUBLISHED", "STATUS_COMPLETED", "STATUS_CANCELLED",
    # ── JoinRequest status
    "STATUS_PENDING", "STATUS_APPROVED", "STATUS_REJECTED", "STATUS_ATTENDED",
    # ── Notification types
    "TYPE_JOIN_REQUEST", "TYPE_APPROVAL", "TYPE_REJECTION",
    "TYPE_EVENT_REMINDER", "TYPE_EVENT_UPDATE", "TYPE_EVENT_CANCELLED",
    "TYPE_ANNOUNCEMENT", "TYPE_SYSTEM", "TYPE_GENERAL",
]
