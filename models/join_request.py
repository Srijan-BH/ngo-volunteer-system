"""
Join Request Model — NGO Volunteer Management System
Collection : join_requests

Schema
------
_id          : ObjectId   (auto)
user_id      : ObjectId   ref → users   (required)
event_id     : ObjectId   ref → events  (required)
status       : str        enum: pending | approved | rejected | withdrawn | attended | no_show
remarks      : str        admin remarks / reason for approval or rejection
user_remarks : str        note from volunteer at time of application
applied_date : datetime   auto  (creation timestamp)
reviewed_by  : ObjectId   ref → admins  (nullable)
reviewed_at  : datetime   nullable
hours_logged : float      volunteer hours credited after attendance
updated_at   : datetime   auto

Unique compound index: (user_id, event_id) — one request per user per event.
MongoDB JSON Schema Validator included via `get_validator()`.
"""

import logging
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId

from database.connection import get_collection, get_db

logger = logging.getLogger(__name__)

COLLECTION = "join_requests"

# ─── Status Constants ─────────────────────────────────────────────────────────
STATUS_PENDING   = "pending"
STATUS_APPROVED  = "approved"
STATUS_REJECTED  = "rejected"
STATUS_WITHDRAWN = "withdrawn"
STATUS_ATTENDED  = "attended"
STATUS_NO_SHOW   = "no_show"
VALID_STATUSES   = {
    STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED,
    STATUS_WITHDRAWN, STATUS_ATTENDED, STATUS_NO_SHOW,
}

# Transitions: which status changes are allowed
ALLOWED_TRANSITIONS = {
    STATUS_PENDING:   {STATUS_APPROVED, STATUS_REJECTED, STATUS_WITHDRAWN},
    STATUS_APPROVED:  {STATUS_ATTENDED, STATUS_NO_SHOW, STATUS_WITHDRAWN},
    STATUS_REJECTED:  set(),
    STATUS_WITHDRAWN: set(),
    STATUS_ATTENDED:  set(),
    STATUS_NO_SHOW:   set(),
}


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _col():
    return get_collection(COLLECTION)


# ─── MongoDB JSON Schema Validator ────────────────────────────────────────────
def get_validator() -> dict:
    return {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["user_id", "event_id", "status", "applied_date"],
            "additionalProperties": True,
            "properties": {
                "user_id": {
                    "bsonType": "objectId",
                    "description": "Reference to users._id — required",
                },
                "event_id": {
                    "bsonType": "objectId",
                    "description": "Reference to events._id — required",
                },
                "status": {
                    "bsonType": "string",
                    "enum": list(VALID_STATUSES),
                    "description": "Request lifecycle status",
                },
                "remarks": {
                    "bsonType": "string",
                    "maxLength": 500,
                    "description": "Admin remarks (approval note / rejection reason)",
                },
                "user_remarks": {
                    "bsonType": "string",
                    "maxLength": 500,
                    "description": "Volunteer's note submitted at application time",
                },
                "applied_date": {
                    "bsonType": "date",
                    "description": "When the request was submitted",
                },
                "reviewed_by": {
                    "bsonType": ["objectId", "null"],
                    "description": "Reference to admins._id who reviewed",
                },
                "reviewed_at": {
                    "bsonType": ["date", "null"],
                    "description": "When the review decision was made",
                },
                "hours_logged": {
                    "bsonType": ["double", "int"],
                    "minimum": 0,
                    "description": "Volunteer hours credited after attendance",
                },
                "rating": {
                    "bsonType": ["int", "null"],
                    "minimum": 1,
                    "maximum": 5,
                    "description": "Star rating out of 5 from the volunteer",
                },
                "feedback": {
                    "bsonType": ["string", "null"],
                    "maxLength": 1000,
                    "description": "Feedback comments from the volunteer",
                },
                "updated_at": {"bsonType": "date"},
            },
        }
    }


def apply_validator():
    """Apply the JSON schema validator to the join_requests collection (idempotent)."""
    db = get_db()
    existing = db.list_collection_names()
    if COLLECTION not in existing:
        db.create_collection(COLLECTION, validator=get_validator())
        logger.info(f"Collection '{COLLECTION}' created with validator.")
    else:
        db.command("collMod", COLLECTION, validator=get_validator(), validationLevel="moderate")
        logger.info(f"Validator applied to existing collection '{COLLECTION}'.")


# ─── Model Class ──────────────────────────────────────────────────────────────
class JoinRequestModel:
    """Static CRUD interface for the `join_requests` collection."""

    # ── Schema Builder ────────────────────────────────────────────────────────
    @staticmethod
    def build_document(
        user_id: str,
        event_id: str,
        user_remarks: str = "",
        status: str = STATUS_PENDING,
    ) -> dict:
        """Build a validated join_request document (NOT yet saved to DB)."""
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{status}'.")
        now = datetime.now(timezone.utc)
        return {
            "user_id":      ObjectId(user_id),
            "event_id":     ObjectId(event_id),
            "status":       status,
            "remarks":      "",
            "user_remarks": user_remarks.strip(),
            "applied_date": now,
            "reviewed_by":  None,
            "reviewed_at":  None,
            "hours_logged": 0.0,
            "rating":       None,
            "feedback":     None,
            "updated_at":   now,
        }

    # ── Create ────────────────────────────────────────────────────────────────
    @staticmethod
    def create(user_id: str, event_id: str, user_remarks: str = "") -> str:
        """Submit a new join request. Returns inserted _id as string."""
        doc    = JoinRequestModel.build_document(user_id, event_id, user_remarks)
        result = _col().insert_one(doc)
        logger.info(
            f"Join request created  id={result.inserted_id} "
            f"user={user_id}  event={event_id}"
        )
        return str(result.inserted_id)

    # ── Read (single) ─────────────────────────────────────────────────────────
    @staticmethod
    def find_by_id(request_id: str) -> dict | None:
        try:
            return _col().find_one({"_id": ObjectId(request_id)})
        except InvalidId:
            return None

    @staticmethod
    def find_by_user_and_event(user_id: str, event_id: str) -> dict | None:
        """Check if a user has already applied for an event."""
        try:
            return _col().find_one({
                "user_id":  ObjectId(user_id),
                "event_id": ObjectId(event_id),
            })
        except InvalidId:
            return None

    # ── Read (list) ───────────────────────────────────────────────────────────
    @staticmethod
    def find_all(
        filters: dict = None,
        page: int = 1,
        page_size: int = 10,
        sort_by: str = "applied_date",
        sort_order: int = -1,
    ) -> tuple[list, int]:
        query = filters or {}
        col   = _col()
        total = col.count_documents(query)
        skip  = (page - 1) * page_size
        docs  = list(col.find(query).sort(sort_by, sort_order).skip(skip).limit(page_size))
        return docs, total

    @staticmethod
    def find_by_event(
        event_id: str,
        status: str = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list, int]:
        try:
            q = {"event_id": ObjectId(event_id)}
            if status:
                q["status"] = status
            return JoinRequestModel.find_all(q, page, page_size)
        except InvalidId:
            return [], 0

    @staticmethod
    def find_by_user(
        user_id: str,
        status: str = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list, int]:
        try:
            q = {"user_id": ObjectId(user_id)}
            if status:
                q["status"] = status
            return JoinRequestModel.find_all(q, page, page_size)
        except InvalidId:
            return [], 0

    @staticmethod
    def find_pending(page: int = 1, page_size: int = 10) -> tuple[list, int]:
        return JoinRequestModel.find_all({"status": STATUS_PENDING}, page, page_size)

    @staticmethod
    def add_feedback(request_id: str, rating: int, feedback: str) -> bool:
        """Add volunteer rating and feedback to a request."""
        try:
            update = {
                "rating": max(1, min(5, int(rating))),
                "feedback": feedback.strip() if feedback else None,
                "updated_at": datetime.now(timezone.utc),
            }
            result = _col().update_one(
                {"_id": ObjectId(request_id)},
                {"$set": update},
            )
            return result.modified_count > 0
        except InvalidId:
            return False

    # ── Update ────────────────────────────────────────────────────────────────
    @staticmethod
    def update(request_id: str, update_data: dict) -> bool:
        try:
            update_data["updated_at"] = datetime.now(timezone.utc)
            result = _col().update_one(
                {"_id": ObjectId(request_id)},
                {"$set": update_data},
            )
            return result.modified_count > 0
        except InvalidId:
            return False

    @staticmethod
    def update_status(
        request_id: str,
        new_status: str,
        reviewed_by: str = None,
        remarks: str = "",
    ) -> bool:
        """
        Change request status with optional reviewer info and remarks.
        Validates against ALLOWED_TRANSITIONS.
        """
        if new_status not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{new_status}'.")

        req = JoinRequestModel.find_by_id(request_id)
        if not req:
            raise LookupError("Join request not found.")

        current = req.get("status")
        if new_status not in ALLOWED_TRANSITIONS.get(current, set()):
            raise ValueError(
                f"Cannot transition from '{current}' to '{new_status}'."
            )

        update = {
            "status":   new_status,
            "remarks":  remarks.strip(),
        }
        if reviewed_by:
            update["reviewed_by"] = ObjectId(reviewed_by)
            update["reviewed_at"] = datetime.now(timezone.utc)

        return JoinRequestModel.update(request_id, update)

    @staticmethod
    def approve(request_id: str, reviewed_by: str, remarks: str = "") -> bool:
        return JoinRequestModel.update_status(request_id, STATUS_APPROVED, reviewed_by, remarks)

    @staticmethod
    def reject(request_id: str, reviewed_by: str, remarks: str = "") -> bool:
        return JoinRequestModel.update_status(request_id, STATUS_REJECTED, reviewed_by, remarks)

    @staticmethod
    def withdraw(request_id: str) -> bool:
        return JoinRequestModel.update_status(request_id, STATUS_WITHDRAWN)

    @staticmethod
    def mark_attended(request_id: str, hours: float = 0.0) -> bool:
        try:
            result = _col().update_one(
                {"_id": ObjectId(request_id)},
                {"$set": {
                    "status":      STATUS_ATTENDED,
                    "hours_logged": round(float(hours), 2),
                    "updated_at":  datetime.now(timezone.utc),
                }},
            )
            return result.modified_count > 0
        except InvalidId:
            return False

    @staticmethod
    def mark_no_show(request_id: str) -> bool:
        return JoinRequestModel.update_status(request_id, STATUS_NO_SHOW)

    # ── Delete ────────────────────────────────────────────────────────────────
    @staticmethod
    def delete(request_id: str) -> bool:
        try:
            result = _col().delete_one({"_id": ObjectId(request_id)})
            return result.deleted_count > 0
        except InvalidId:
            return False

    # ── Aggregations ──────────────────────────────────────────────────────────
    @staticmethod
    def count_by_status(event_id: str = None) -> list:
        match = {"event_id": ObjectId(event_id)} if event_id else {}
        pipeline = [
            *([ {"$match": match} ] if match else []),
            {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        ]
        return list(_col().aggregate(pipeline))

    @staticmethod
    def total_hours_by_user(user_id: str) -> float:
        try:
            pipeline = [
                {"$match": {"user_id": ObjectId(user_id), "status": STATUS_ATTENDED}},
                {"$group": {"_id": None, "total": {"$sum": "$hours_logged"}}},
            ]
            result = list(_col().aggregate(pipeline))
            return result[0]["total"] if result else 0.0
        except InvalidId:
            return 0.0

    @staticmethod
    def event_attendance_rate(event_id: str) -> dict:
        """Return approved, attended, no_show counts for an event."""
        try:
            pipeline = [
                {"$match": {"event_id": ObjectId(event_id)}},
                {"$group": {"_id": "$status", "count": {"$sum": 1}}},
            ]
            raw    = {r["_id"]: r["count"] for r in _col().aggregate(pipeline)}
            approved = raw.get(STATUS_APPROVED, 0)
            attended = raw.get(STATUS_ATTENDED, 0)
            no_show  = raw.get(STATUS_NO_SHOW, 0)
            total    = approved + attended + no_show
            rate     = round(attended / total * 100, 1) if total > 0 else 0.0
            return {
                "approved": approved,
                "attended": attended,
                "no_show":  no_show,
                "attendance_rate_pct": rate,
            }
        except InvalidId:
            return {}

    # ── Serialization ─────────────────────────────────────────────────────────
    @staticmethod
    def serialize(req: dict) -> dict:
        if not req:
            return {}
        return {
            "id":           str(req["_id"]),
            "user_id":      str(req.get("user_id", "")),
            "event_id":     str(req.get("event_id", "")),
            "status":       req.get("status"),
            "remarks":      req.get("remarks", ""),
            "user_remarks": req.get("user_remarks", ""),
            "applied_date": req.get("applied_date").isoformat() if req.get("applied_date") else None,
            "reviewed_by":  str(req["reviewed_by"]) if req.get("reviewed_by") else None,
            "reviewed_at":  req.get("reviewed_at").isoformat() if req.get("reviewed_at") else None,
            "hours_logged": req.get("hours_logged", 0.0),
            "rating":       req.get("rating"),
            "feedback":     req.get("feedback"),
            "updated_at":   req.get("updated_at").isoformat() if req.get("updated_at") else None,
        }
