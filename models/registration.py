"""
Registration Model
Tracks volunteer registrations for events.
"""

import logging
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId

from database.connection import get_collection

logger = logging.getLogger(__name__)

COLLECTION = "registrations"

# ─── Status Constants ─────────────────────────────────────────────────────────
STATUS_PENDING = "pending"
STATUS_CONFIRMED = "confirmed"
STATUS_WAITLISTED = "waitlisted"
STATUS_CANCELLED = "cancelled"
STATUS_ATTENDED = "attended"
STATUS_NO_SHOW = "no_show"
VALID_STATUSES = {
    STATUS_PENDING, STATUS_CONFIRMED, STATUS_WAITLISTED,
    STATUS_CANCELLED, STATUS_ATTENDED, STATUS_NO_SHOW
}


def _collection():
    return get_collection(COLLECTION)


class RegistrationModel:
    """Provides static methods for CRUD on the registrations collection."""

    @staticmethod
    def build_document(
        volunteer_id: str,
        event_id: str,
        status: str = STATUS_PENDING,
        notes: str = "",
    ) -> dict:
        now = datetime.now(timezone.utc)
        return {
            "volunteer_id": ObjectId(volunteer_id),
            "event_id": ObjectId(event_id),
            "status": status,
            "notes": notes.strip(),
            "hours_logged": 0.0,
            "feedback": None,
            "rating": None,
            "registered_at": now,
            "updated_at": now,
        }

    # ─── Create ───────────────────────────────────────────────────────────────
    @staticmethod
    def create(volunteer_id: str, event_id: str, notes: str = "") -> str:
        doc = RegistrationModel.build_document(volunteer_id, event_id, notes=notes)
        result = _collection().insert_one(doc)
        logger.info(f"Registration created: {result.inserted_id}")
        return str(result.inserted_id)

    # ─── Read ─────────────────────────────────────────────────────────────────
    @staticmethod
    def find_by_id(registration_id: str) -> dict | None:
        try:
            return _collection().find_one({"_id": ObjectId(registration_id)})
        except InvalidId:
            return None

    @staticmethod
    def find_by_volunteer_and_event(volunteer_id: str, event_id: str) -> dict | None:
        try:
            return _collection().find_one({
                "volunteer_id": ObjectId(volunteer_id),
                "event_id": ObjectId(event_id),
            })
        except InvalidId:
            return None

    @staticmethod
    def find_by_event(
        event_id: str,
        status: str = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list, int]:
        try:
            query = {"event_id": ObjectId(event_id)}
            if status:
                query["status"] = status
            col = _collection()
            total = col.count_documents(query)
            skip = (page - 1) * page_size
            cursor = col.find(query).sort("registered_at", -1).skip(skip).limit(page_size)
            return list(cursor), total
        except InvalidId:
            return [], 0

    @staticmethod
    def find_by_volunteer(
        volunteer_id: str,
        status: str = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list, int]:
        try:
            query = {"volunteer_id": ObjectId(volunteer_id)}
            if status:
                query["status"] = status
            col = _collection()
            total = col.count_documents(query)
            skip = (page - 1) * page_size
            cursor = col.find(query).sort("registered_at", -1).skip(skip).limit(page_size)
            return list(cursor), total
        except InvalidId:
            return [], 0

    # ─── Update ───────────────────────────────────────────────────────────────
    @staticmethod
    def update_status(registration_id: str, status: str) -> bool:
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{status}'.")
        try:
            result = _collection().update_one(
                {"_id": ObjectId(registration_id)},
                {"$set": {"status": status, "updated_at": datetime.now(timezone.utc)}},
            )
            return result.modified_count > 0
        except InvalidId:
            return False

    @staticmethod
    def log_hours(registration_id: str, hours: float, feedback: str = "", rating: int = None) -> bool:
        try:
            update = {
                "hours_logged": hours,
                "status": STATUS_ATTENDED,
                "updated_at": datetime.now(timezone.utc),
            }
            if feedback:
                update["feedback"] = feedback.strip()
            if rating is not None:
                update["rating"] = max(1, min(5, int(rating)))
            result = _collection().update_one(
                {"_id": ObjectId(registration_id)},
                {"$set": update},
            )
            return result.modified_count > 0
        except InvalidId:
            return False

    # ─── Delete ───────────────────────────────────────────────────────────────
    @staticmethod
    def delete(registration_id: str) -> bool:
        try:
            result = _collection().delete_one({"_id": ObjectId(registration_id)})
            return result.deleted_count > 0
        except InvalidId:
            return False

    # ─── Serialization ────────────────────────────────────────────────────────
    @staticmethod
    def serialize(reg: dict) -> dict:
        if not reg:
            return {}
        return {
            "id": str(reg["_id"]),
            "volunteer_id": str(reg.get("volunteer_id", "")),
            "event_id": str(reg.get("event_id", "")),
            "status": reg.get("status"),
            "notes": reg.get("notes"),
            "hours_logged": reg.get("hours_logged", 0.0),
            "feedback": reg.get("feedback"),
            "rating": reg.get("rating"),
            "registered_at": reg.get("registered_at").isoformat() if reg.get("registered_at") else None,
            "updated_at": reg.get("updated_at").isoformat() if reg.get("updated_at") else None,
        }
