"""
Volunteer Model
Handles volunteer profiles, skills, availability, and status tracking.
"""

import logging
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId

from database.connection import get_collection

logger = logging.getLogger(__name__)

COLLECTION = "volunteers"

# ─── Status Constants ─────────────────────────────────────────────────────────
STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUS_SUSPENDED = "suspended"
VALID_STATUSES = {STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED, STATUS_SUSPENDED}

# ─── Availability Constants ───────────────────────────────────────────────────
AVAILABILITY_WEEKDAYS = "weekdays"
AVAILABILITY_WEEKENDS = "weekends"
AVAILABILITY_FULL_TIME = "full_time"
AVAILABILITY_PART_TIME = "part_time"
AVAILABILITY_FLEXIBLE = "flexible"


def _collection():
    return get_collection(COLLECTION)


class VolunteerModel:
    """Provides static methods for CRUD on the volunteers collection."""

    @staticmethod
    def build_document(
        user_id: str,
        bio: str = "",
        skills: list = None,
        interests: list = None,
        availability: str = AVAILABILITY_FLEXIBLE,
        location: str = "",
        emergency_contact_name: str = "",
        emergency_contact_phone: str = "",
        hours_contributed: float = 0.0,
        status: str = STATUS_PENDING,
    ) -> dict:
        now = datetime.now(timezone.utc)
        return {
            "user_id": ObjectId(user_id),
            "bio": bio.strip(),
            "skills": skills or [],
            "interests": interests or [],
            "availability": availability,
            "location": location.strip(),
            "emergency_contact": {
                "name": emergency_contact_name.strip(),
                "phone": emergency_contact_phone.strip(),
            },
            "hours_contributed": hours_contributed,
            "status": status,
            "events_registered": [],
            "events_attended": [],
            "certifications": [],
            "created_at": now,
            "updated_at": now,
        }

    # ─── Create ───────────────────────────────────────────────────────────────
    @staticmethod
    def create(data: dict) -> str:
        doc = VolunteerModel.build_document(**data)
        result = _collection().insert_one(doc)
        logger.info(f"Volunteer profile created: {result.inserted_id}")
        return str(result.inserted_id)

    # ─── Read ─────────────────────────────────────────────────────────────────
    @staticmethod
    def find_by_id(volunteer_id: str) -> dict | None:
        try:
            return _collection().find_one({"_id": ObjectId(volunteer_id)})
        except InvalidId:
            return None

    @staticmethod
    def find_by_user_id(user_id: str) -> dict | None:
        try:
            return _collection().find_one({"user_id": ObjectId(user_id)})
        except InvalidId:
            return None

    @staticmethod
    def find_all(
        filters: dict = None,
        page: int = 1,
        page_size: int = 10,
        sort_by: str = "created_at",
        sort_order: int = -1,
    ) -> tuple[list, int]:
        query = filters or {}
        col = _collection()
        total = col.count_documents(query)
        skip = (page - 1) * page_size
        cursor = col.find(query).sort(sort_by, sort_order).skip(skip).limit(page_size)
        return list(cursor), total

    @staticmethod
    def find_by_skills(skills: list) -> list:
        return list(_collection().find({"skills": {"$in": skills}}))

    # ─── Update ───────────────────────────────────────────────────────────────
    @staticmethod
    def update(volunteer_id: str, update_data: dict) -> bool:
        try:
            update_data["updated_at"] = datetime.now(timezone.utc)
            result = _collection().update_one(
                {"_id": ObjectId(volunteer_id)},
                {"$set": update_data},
            )
            return result.modified_count > 0
        except InvalidId:
            return False

    @staticmethod
    def update_status(volunteer_id: str, status: str) -> bool:
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{status}'.")
        return VolunteerModel.update(volunteer_id, {"status": status})

    @staticmethod
    def add_hours(volunteer_id: str, hours: float) -> bool:
        try:
            result = _collection().update_one(
                {"_id": ObjectId(volunteer_id)},
                {
                    "$inc": {"hours_contributed": hours},
                    "$set": {"updated_at": datetime.now(timezone.utc)},
                },
            )
            return result.modified_count > 0
        except InvalidId:
            return False

    # ─── Delete ───────────────────────────────────────────────────────────────
    @staticmethod
    def delete(volunteer_id: str) -> bool:
        try:
            result = _collection().delete_one({"_id": ObjectId(volunteer_id)})
            return result.deleted_count > 0
        except InvalidId:
            return False

    # ─── Serialization ────────────────────────────────────────────────────────
    @staticmethod
    def serialize(volunteer: dict) -> dict:
        if not volunteer:
            return {}
        return {
            "id": str(volunteer["_id"]),
            "user_id": str(volunteer.get("user_id", "")),
            "bio": volunteer.get("bio"),
            "skills": volunteer.get("skills", []),
            "interests": volunteer.get("interests", []),
            "availability": volunteer.get("availability"),
            "location": volunteer.get("location"),
            "emergency_contact": volunteer.get("emergency_contact", {}),
            "hours_contributed": volunteer.get("hours_contributed", 0.0),
            "status": volunteer.get("status"),
            "events_registered": [str(e) for e in volunteer.get("events_registered", [])],
            "events_attended": [str(e) for e in volunteer.get("events_attended", [])],
            "certifications": volunteer.get("certifications", []),
            "created_at": volunteer.get("created_at").isoformat() if volunteer.get("created_at") else None,
            "updated_at": volunteer.get("updated_at").isoformat() if volunteer.get("updated_at") else None,
        }
