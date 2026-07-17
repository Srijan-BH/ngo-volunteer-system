"""
Notification Model — NGO Volunteer Management System
Collection : notifications

Schema
------
_id          : ObjectId   (auto)
user_id      : ObjectId   ref → users   (required)
title        : str        required
message      : str        required
type         : str        enum: join_request | event_reminder | event_update |
                               event_cancelled | approval | rejection |
                               announcement | system | general
is_read      : bool       default False
read_at      : datetime   nullable — set when is_read becomes True
related_id   : ObjectId   nullable — ref to an event / join_request / etc.
related_model: str        nullable — "event" | "join_request" | etc.
created_at   : datetime   auto  (also used for TTL index — 90 days)

TTL Index: auto-delete notifications older than 90 days (7,776,000 seconds).
MongoDB JSON Schema Validator included via `get_validator()`.
"""

import logging
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId

from database.connection import get_collection, get_db

logger = logging.getLogger(__name__)

COLLECTION = "notifications"

# ─── Notification Types ───────────────────────────────────────────────────────
TYPE_JOIN_REQUEST   = "join_request"
TYPE_EVENT_REMINDER = "event_reminder"
TYPE_EVENT_UPDATE   = "event_update"
TYPE_EVENT_CANCELLED= "event_cancelled"
TYPE_APPROVAL       = "approval"
TYPE_REJECTION      = "rejection"
TYPE_ANNOUNCEMENT   = "announcement"
TYPE_SYSTEM         = "system"
TYPE_GENERAL        = "general"
TYPE_CERTIFICATE    = "certificate"

# Aliases for backwards compatibility with EventController
TYPE_REGISTRATION_CONFIRMED = TYPE_APPROVAL
TYPE_EVENT_UPDATED = TYPE_EVENT_UPDATE

VALID_TYPES = {
    TYPE_JOIN_REQUEST, TYPE_EVENT_REMINDER, TYPE_EVENT_UPDATE,
    TYPE_EVENT_CANCELLED, TYPE_APPROVAL, TYPE_REJECTION,
    TYPE_ANNOUNCEMENT, TYPE_SYSTEM, TYPE_GENERAL, TYPE_CERTIFICATE
}


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _col():
    return get_collection(COLLECTION)


# ─── MongoDB JSON Schema Validator ────────────────────────────────────────────
def get_validator() -> dict:
    return {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["user_id", "title", "message", "type", "is_read", "created_at"],
            "additionalProperties": True,
            "properties": {
                "user_id": {
                    "bsonType": "objectId",
                    "description": "Reference to users._id — required",
                },
                "title": {
                    "bsonType": "string",
                    "minLength": 1,
                    "maxLength": 200,
                    "description": "Short notification title — required",
                },
                "message": {
                    "bsonType": "string",
                    "minLength": 1,
                    "maxLength": 1000,
                    "description": "Notification body message — required",
                },
                "type": {
                    "bsonType": "string",
                    "enum": list(VALID_TYPES),
                    "description": "Notification category type",
                },
                "is_read": {
                    "bsonType": "bool",
                    "description": "Whether the user has read this notification",
                },
                "read_at": {
                    "bsonType": ["date", "null"],
                    "description": "Timestamp when the notification was first read",
                },
                "related_id": {
                    "bsonType": ["objectId", "null"],
                    "description": "Reference ID to the related document (event, join_request, etc.)",
                },
                "related_model": {
                    "bsonType": ["string", "null"],
                    "description": "Name of the related collection e.g. 'event', 'join_request'",
                },
                "created_at": {
                    "bsonType": "date",
                    "description": "Creation timestamp — also used for TTL expiry",
                },
            },
        }
    }


def apply_validator():
    """Apply the JSON schema validator to the notifications collection (idempotent)."""
    db = get_db()
    existing = db.list_collection_names()
    if COLLECTION not in existing:
        db.create_collection(COLLECTION, validator=get_validator())
        logger.info(f"Collection '{COLLECTION}' created with validator.")
    else:
        db.command("collMod", COLLECTION, validator=get_validator(), validationLevel="moderate")
        logger.info(f"Validator applied to existing collection '{COLLECTION}'.")


# ─── Model Class ──────────────────────────────────────────────────────────────
class NotificationModel:
    """Static CRUD interface for the `notifications` collection."""

    # ── Schema Builder ────────────────────────────────────────────────────────
    @staticmethod
    def build_document(
        user_id: str,
        title: str,
        message: str,
        notification_type: str = TYPE_GENERAL,
        related_id: str = None,
        related_model: str = None,
    ) -> dict:
        """Build a validated notification document (NOT yet saved to DB)."""
        if notification_type not in VALID_TYPES:
            raise ValueError(f"Invalid type '{notification_type}'. Choose from: {VALID_TYPES}")

        now = datetime.now(timezone.utc)
        doc = {
            "user_id":       ObjectId(user_id),
            "title":         title.strip(),
            "message":       message.strip(),
            "type":          notification_type,
            "is_read":       False,
            "read_at":       None,
            "related_id":    ObjectId(related_id) if related_id else None,
            "related_model": related_model.strip() if related_model else None,
            "created_at":    now,
        }
        return doc

    # ── Create ────────────────────────────────────────────────────────────────
    @staticmethod
    def create(
        user_id: str,
        title: str,
        message: str,
        notification_type: str = TYPE_GENERAL,
        related_id: str = None,
        related_model: str = None,
    ) -> str:
        """Insert a new notification. Returns inserted _id as string."""
        doc    = NotificationModel.build_document(
            user_id, title, message, notification_type, related_id, related_model
        )
        result = _col().insert_one(doc)
        logger.debug(
            f"Notification created  id={result.inserted_id} "
            f"user={user_id}  type={notification_type}"
        )
        return str(result.inserted_id)

    @staticmethod
    def send_bulk(
        user_ids: list,
        title: str,
        message: str,
        notification_type: str = TYPE_ANNOUNCEMENT,
        related_id: str = None,
        related_model: str = None,
    ) -> int:
        """Send the same notification to multiple users. Returns insert count."""
        if not user_ids:
            return 0
        docs = [
            NotificationModel.build_document(
                uid, title, message, notification_type, related_id, related_model
            )
            for uid in user_ids
        ]
        result = _col().insert_many(docs)
        logger.info(f"Bulk notification sent  count={len(result.inserted_ids)}")
        return len(result.inserted_ids)

    # ── Read (single) ─────────────────────────────────────────────────────────
    @staticmethod
    def find_by_id(notif_id: str) -> dict | None:
        try:
            return _col().find_one({"_id": ObjectId(notif_id)})
        except InvalidId:
            return None

    # ── Read (list) ───────────────────────────────────────────────────────────
    @staticmethod
    def find_by_user(
        user_id: str,
        is_read: bool = None,
        notification_type: str = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list, int]:
        """Return paginated notifications for a user."""
        try:
            q = {"user_id": ObjectId(user_id)}
            if is_read is not None:
                q["is_read"] = is_read
            if notification_type:
                q["type"] = notification_type
            col   = _col()
            total = col.count_documents(q)
            skip  = (page - 1) * page_size
            docs  = list(col.find(q).sort("created_at", -1).skip(skip).limit(page_size))
            return docs, total
        except InvalidId:
            return [], 0

    @staticmethod
    def find_unread(user_id: str, page: int = 1, page_size: int = 20) -> tuple[list, int]:
        return NotificationModel.find_by_user(user_id, is_read=False, page=page, page_size=page_size)

    @staticmethod
    def count_unread(user_id: str) -> int:
        try:
            return _col().count_documents({"user_id": ObjectId(user_id), "is_read": False})
        except InvalidId:
            return 0

    # ── Update ────────────────────────────────────────────────────────────────
    @staticmethod
    def mark_read(notif_id: str) -> bool:
        """Mark a single notification as read."""
        try:
            result = _col().update_one(
                {"_id": ObjectId(notif_id), "is_read": False},
                {"$set": {"is_read": True, "read_at": datetime.now(timezone.utc)}},
            )
            return result.modified_count > 0
        except InvalidId:
            return False

    @staticmethod
    def mark_all_read(user_id: str) -> int:
        """Mark ALL unread notifications as read for a user. Returns modified count."""
        try:
            now    = datetime.now(timezone.utc)
            result = _col().update_many(
                {"user_id": ObjectId(user_id), "is_read": False},
                {"$set": {"is_read": True, "read_at": now}},
            )
            return result.modified_count
        except InvalidId:
            return 0

    @staticmethod
    def mark_read_by_related(user_id: str, related_id: str, related_model: str) -> int:
        """Mark all notifications related to a specific document as read."""
        try:
            now    = datetime.now(timezone.utc)
            result = _col().update_many(
                {
                    "user_id":       ObjectId(user_id),
                    "related_id":    ObjectId(related_id),
                    "related_model": related_model,
                    "is_read":       False,
                },
                {"$set": {"is_read": True, "read_at": now}},
            )
            return result.modified_count
        except InvalidId:
            return 0

    # ── Delete ────────────────────────────────────────────────────────────────
    @staticmethod
    def delete(notif_id: str) -> bool:
        try:
            result = _col().delete_one({"_id": ObjectId(notif_id)})
            return result.deleted_count > 0
        except InvalidId:
            return False

    @staticmethod
    def delete_all_for_user(user_id: str) -> int:
        try:
            result = _col().delete_many({"user_id": ObjectId(user_id)})
            return result.deleted_count
        except InvalidId:
            return 0

    @staticmethod
    def delete_read(user_id: str) -> int:
        """Delete all read notifications for a user."""
        try:
            result = _col().delete_many({"user_id": ObjectId(user_id), "is_read": True})
            return result.deleted_count
        except InvalidId:
            return 0

    # ── Factory Helpers (typed constructors) ──────────────────────────────────
    @staticmethod
    def notify_join_request(user_id: str, event_title: str, event_id: str) -> str:
        return NotificationModel.create(
            user_id=user_id,
            title="Join Request Submitted",
            message=f"Your request to join '{event_title}' has been received and is under review.",
            notification_type=TYPE_JOIN_REQUEST,
            related_id=event_id,
            related_model="event",
        )

    @staticmethod
    def notify_approval(user_id: str, event_title: str, event_id: str) -> str:
        return NotificationModel.create(
            user_id=user_id,
            title="Request Approved! 🎉",
            message=f"Your request to join '{event_title}' has been approved. See you there!",
            notification_type=TYPE_APPROVAL,
            related_id=event_id,
            related_model="event",
        )

    @staticmethod
    def notify_rejection(user_id: str, event_title: str, event_id: str, reason: str = "") -> str:
        msg = f"Your request to join '{event_title}' was not approved."
        if reason:
            msg += f" Reason: {reason}"
        return NotificationModel.create(
            user_id=user_id,
            title="Request Not Approved",
            message=msg,
            notification_type=TYPE_REJECTION,
            related_id=event_id,
            related_model="event",
        )

    @staticmethod
    def notify_event_update(user_id: str, event_title: str, event_id: str, change: str = "") -> str:
        msg = f"The event '{event_title}' has been updated."
        if change:
            msg += f" Change: {change}"
        return NotificationModel.create(
            user_id=user_id,
            title="Event Updated",
            message=msg,
            notification_type=TYPE_EVENT_UPDATE,
            related_id=event_id,
            related_model="event",
        )

    @staticmethod
    def notify_event_cancelled(user_id: str, event_title: str, event_id: str) -> str:
        return NotificationModel.create(
            user_id=user_id,
            title="Event Cancelled",
            message=f"We regret to inform you that the event '{event_title}' has been cancelled.",
            notification_type=TYPE_EVENT_CANCELLED,
            related_id=event_id,
            related_model="event",
        )

    @staticmethod
    def notify_reminder(user_id: str, event_title: str, event_id: str, days: int = 1) -> str:
        return NotificationModel.create(
            user_id=user_id,
            title=f"Event Reminder — {days} day(s) to go!",
            message=f"'{event_title}' is happening in {days} day(s). Don't forget to attend!",
            notification_type=TYPE_EVENT_REMINDER,
            related_id=event_id,
            related_model="event",
        )

    @staticmethod
    def notify_certificate_available(user_id: str, event_title: str, request_id: str) -> str:
        return NotificationModel.create(
            user_id=user_id,
            title="Certificate of Appreciation",
            message=f"Thank you for attending '{event_title}'! Your certificate is now available.",
            notification_type=TYPE_CERTIFICATE,
            related_id=request_id,
            related_model="join_request",
        )

    # ── Aggregations ──────────────────────────────────────────────────────────
    @staticmethod
    def summary_for_user(user_id: str) -> dict:
        """Quick summary: total, unread, by type."""
        try:
            pipeline = [
                {"$match": {"user_id": ObjectId(user_id)}},
                {"$group": {
                    "_id":        "$type",
                    "total":      {"$sum": 1},
                    "unread":     {"$sum": {"$cond": [{"$eq": ["$is_read", False]}, 1, 0]}},
                }},
            ]
            by_type      = list(_col().aggregate(pipeline))
            total_unread = _col().count_documents({"user_id": ObjectId(user_id), "is_read": False})
            total        = _col().count_documents({"user_id": ObjectId(user_id)})
            return {
                "total":         total,
                "total_unread":  total_unread,
                "by_type":       by_type,
            }
        except InvalidId:
            return {}

    # ── Serialization ─────────────────────────────────────────────────────────
    @staticmethod
    def serialize(notif: dict) -> dict:
        if not notif:
            return {}
            
        def _format_dt(dt):
            if not dt: return None
            if not dt.tzinfo:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
            
        out = {
            "id":            str(notif["_id"]),
            "user_id":       str(notif.get("user_id", "")),
            "title":         notif.get("title"),
            "message":       notif.get("message"),
            "type":          notif.get("type"),
            "is_read":       notif.get("is_read", False),
            "read_at":       _format_dt(notif.get("read_at")),
            "created_at":    _format_dt(notif.get("created_at")),
        }
        if notif.get("related_id"):
            out["related"] = {
                "id":    str(notif["related_id"]),
                "model": notif.get("related_model"),
            }
        return out
