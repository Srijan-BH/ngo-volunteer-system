"""
Event Model — NGO Volunteer Management System
Collection : events

Schema
------
_id                  : ObjectId    (auto)
title                : str         required
description          : str         required
category_id          : ObjectId    ref → categories
category_name        : str         denormalised for fast reads
date                 : date        required  (YYYY-MM-DD stored as datetime at 00:00 UTC)
start_time           : str         required  "HH:MM"  24-hour format
end_time             : str         required  "HH:MM"  24-hour format
location             : dict        { venue, address, city, state, country, map_link }
banner_image         : str         filename / relative URL
max_participants     : int         0 = unlimited
current_participants : int         auto-maintained
status               : str         enum: draft | published | ongoing | completed | cancelled
created_by           : ObjectId    ref → admins
tags                 : list[str]   for search
views                : int         page-view counter
created_at           : datetime    auto
updated_at           : datetime    auto

MongoDB JSON Schema Validator included via `get_validator()`.
"""

import logging
from datetime import datetime, timezone, date as date_type
from bson import ObjectId
from bson.errors import InvalidId

from database.connection import get_collection, get_db

logger = logging.getLogger(__name__)

COLLECTION = "events"

# ─── Status Constants ─────────────────────────────────────────────────────────
STATUS_DRAFT     = "draft"
STATUS_PUBLISHED = "published"
STATUS_ONGOING   = "ongoing"
STATUS_COMPLETED = "completed"
STATUS_CANCELLED = "cancelled"
VALID_STATUSES   = {STATUS_DRAFT, STATUS_PUBLISHED, STATUS_ONGOING, STATUS_COMPLETED, STATUS_CANCELLED}


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _col():
    return get_collection(COLLECTION)


def _parse_date(value) -> datetime:
    """Accept date / datetime / ISO string → aware UTC datetime at midnight."""
    if isinstance(value, datetime):
        return value.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    if isinstance(value, date_type):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            d = datetime.fromisoformat(value)
            return d.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
        except ValueError:
            raise ValueError(f"Invalid date format: '{value}'. Use ISO 8601 (YYYY-MM-DD).")
    raise TypeError(f"Unsupported date type: {type(value)}")


def _validate_time(t: str) -> str:
    """Validate HH:MM format and return normalised string."""
    t = t.strip()
    try:
        parts = t.split(":")
        assert len(parts) == 2
        h, m = int(parts[0]), int(parts[1])
        assert 0 <= h <= 23 and 0 <= m <= 59
    except (ValueError, AssertionError):
        raise ValueError(f"Invalid time '{t}'. Use HH:MM (24-hour).")
    return f"{h:02d}:{m:02d}"


# ─── MongoDB JSON Schema Validator ────────────────────────────────────────────
def get_validator() -> dict:
    return {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["title", "description", "date", "start_time", "end_time", "status"],
            "additionalProperties": True,
            "properties": {
                "title": {
                    "bsonType": "string",
                    "minLength": 3,
                    "maxLength": 200,
                    "description": "Event title — required",
                },
                "description": {
                    "bsonType": "string",
                    "minLength": 10,
                    "description": "Full event description — required",
                },
                "category_id": {
                    "bsonType": ["objectId", "null"],
                    "description": "Reference to categories._id",
                },
                "category_name": {
                    "bsonType": "string",
                    "description": "Denormalised category name for fast reads",
                },
                "date": {
                    "bsonType": "date",
                    "description": "Event date stored as UTC datetime at midnight",
                },
                "start_time": {
                    "bsonType": "string",
                    "pattern": r"^([01]\d|2[0-3]):([0-5]\d)$",
                    "description": "Start time in HH:MM 24-hour format",
                },
                "end_time": {
                    "bsonType": "string",
                    "pattern": r"^([01]\d|2[0-3]):([0-5]\d)$",
                    "description": "End time in HH:MM 24-hour format",
                },
                "location": {
                    "bsonType": "object",
                    "properties": {
                        "venue":    {"bsonType": "string"},
                        "address":  {"bsonType": "string"},
                        "city":     {"bsonType": "string"},
                        "state":    {"bsonType": "string"},
                        "country":  {"bsonType": "string"},
                        "map_link": {"bsonType": "string"},
                    },
                    "description": "Structured location",
                },
                "location_geo": {
                    "bsonType": ["object", "null"],
                    "properties": {
                        "type": {"enum": ["Point"]},
                        "coordinates": {
                            "bsonType": "array",
                            "minItems": 2,
                            "maxItems": 2,
                            "items": {"bsonType": "double"}
                        }
                    },
                    "description": "GeoJSON Point for spatial queries",
                },
                "banner_image": {
                    "bsonType": "string",
                    "description": "Filename or relative URL of banner image",
                },
                "max_participants": {
                    "bsonType": "int",
                    "minimum": 0,
                    "description": "Maximum participant capacity (0 = unlimited)",
                },
                "current_participants": {
                    "bsonType": "int",
                    "minimum": 0,
                    "description": "Real-time count of confirmed participants",
                },
                "status": {
                    "bsonType": "string",
                    "enum": list(VALID_STATUSES),
                    "description": "Event lifecycle status",
                },
                "created_by": {
                    "bsonType": ["objectId", "null"],
                    "description": "Reference to admins._id",
                },
                "tags": {
                    "bsonType": "array",
                    "items": {"bsonType": "string"},
                },
                "views":      {"bsonType": "int", "minimum": 0},
                "created_at": {"bsonType": "date"},
                "updated_at": {"bsonType": "date"},
            },
        }
    }


def apply_validator():
    """Apply the JSON schema validator to the events collection (idempotent)."""
    db = get_db()
    existing = db.list_collection_names()
    if COLLECTION not in existing:
        db.create_collection(COLLECTION, validator=get_validator())
        logger.info(f"Collection '{COLLECTION}' created with validator.")
    else:
        db.command("collMod", COLLECTION, validator=get_validator(), validationLevel="moderate")
        logger.info(f"Validator applied to existing collection '{COLLECTION}'.")


# ─── Model Class ──────────────────────────────────────────────────────────────
class EventModel:
    """Static CRUD interface for the `events` collection."""

    # ── Schema Builder ────────────────────────────────────────────────────────
    @staticmethod
    def build_document(
        title: str,
        description: str,
        date,                           # date | datetime | ISO str
        start_time: str,
        end_time: str,
        created_by: str = None,
        category_id: str = None,
        category_name: str = "",
        location: dict = None,
        banner_image: str = "",
        max_participants: int = 0,
        status: str = STATUS_DRAFT,
        tags: list = None,
    ) -> dict:
        """Build a validated event document (NOT yet saved to DB)."""
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{status}'. Choose from: {VALID_STATUSES}")

        now = datetime.now(timezone.utc)
        loc = location or {}
        return {
            "title":               title.strip(),
            "description":         description.strip(),
            "category_id":         ObjectId(category_id) if category_id else None,
            "category_name":       category_name.strip(),
            "date":                _parse_date(date),
            "start_time":          _validate_time(start_time),
            "end_time":            _validate_time(end_time),
            "location": {
                "venue":    loc.get("venue", "").strip(),
                "address":  loc.get("address", "").strip(),
                "city":     loc.get("city", "").strip(),
                "state":    loc.get("state", "").strip(),
                "country":  loc.get("country", "").strip(),
                "map_link": loc.get("map_link", "").strip(),
            },
            "location_geo":        loc.get("geo", None),
            "banner_image":        banner_image.strip(),
            "max_participants":    max(0, int(max_participants)),
            "current_participants": 0,
            "status":              status,
            "created_by":          ObjectId(created_by) if created_by else None,
            "tags":                [t.strip().lower() for t in (tags or [])],
            "views":               0,
            "created_at":          now,
            "updated_at":          now,
        }

    # ── Create ────────────────────────────────────────────────────────────────
    @staticmethod
    def create(data: dict) -> str:
        doc    = EventModel.build_document(**data)
        result = _col().insert_one(doc)
        logger.info(f"Event created  id={result.inserted_id}  title='{doc['title']}'")
        return str(result.inserted_id)

    # ── Read (single) ─────────────────────────────────────────────────────────
    @staticmethod
    def find_by_id(event_id: str) -> dict | None:
        try:
            return _col().find_one({"_id": ObjectId(event_id)})
        except InvalidId:
            return None

    # ── Read (list) ───────────────────────────────────────────────────────────
    @staticmethod
    def find_all(
        filters: dict = None,
        page: int = 1,
        page_size: int = 10,
        sort_by: str = "date",
        sort_order: int = 1,
    ) -> tuple[list, int]:
        query = filters or {}
        col   = _col()
        total = col.count_documents(query)
        skip  = (page - 1) * page_size
        docs  = list(col.find(query).sort(sort_by, sort_order).skip(skip).limit(page_size))
        return docs, total

    @staticmethod
    def find_by_status(
        status: str,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list, int]:
        return EventModel.find_all({"status": status}, page, page_size)

    @staticmethod
    def find_by_category(
        category_id: str,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list, int]:
        try:
            return EventModel.find_all({"category_id": ObjectId(category_id)}, page, page_size)
        except InvalidId:
            return [], 0

    @staticmethod
    def find_upcoming(limit: int = 10) -> list:
        now = datetime.now(timezone.utc)
        docs, _ = EventModel.find_all(
            {"date": {"$gte": now}, "status": STATUS_PUBLISHED},
            page_size=limit,
        )
        return docs

    @staticmethod
    def find_by_date_range(start: datetime, end: datetime) -> list:
        docs, _ = EventModel.find_all({"date": {"$gte": start, "$lte": end}})
        return docs

    @staticmethod
    def search(query_str: str, filters: dict = None, page: int = 1, page_size: int = 10) -> tuple[list, int]:
        """Full-text search (requires text index on title + description)."""
        q = {"$text": {"$search": query_str}}
        if filters:
            q.update(filters)
        col   = _col()
        total = col.count_documents(q)
        skip  = (page - 1) * page_size
        docs  = list(
            col.find(q, {"score": {"$meta": "textScore"}})
               .sort([("score", {"$meta": "textScore"})])
               .skip(skip).limit(page_size)
        )
        return docs, total

    @staticmethod
    def check_capacity(event_id: str) -> dict:
        """Return capacity info: max, current, available, is_full."""
        event = EventModel.find_by_id(event_id)
        if not event:
            return {}
        mx      = event.get("max_participants", 0)
        current = event.get("current_participants", 0)
        avail   = (mx - current) if mx > 0 else None
        return {
            "max_participants":     mx,
            "current_participants": current,
            "available_spots":      avail,
            "is_full":             (current >= mx) if mx > 0 else False,
            "is_unlimited":         mx == 0,
        }

    # ── Update ────────────────────────────────────────────────────────────────
    @staticmethod
    def update(event_id: str, update_data: dict) -> bool:
        try:
            update_data["updated_at"] = datetime.now(timezone.utc)
            result = _col().update_one(
                {"_id": ObjectId(event_id)},
                {"$set": update_data},
            )
            return result.modified_count > 0
        except InvalidId:
            return False

    @staticmethod
    def update_status(event_id: str, status: str) -> bool:
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{status}'.")
        return EventModel.update(event_id, {"status": status})

    @staticmethod
    def update_banner(event_id: str, filename: str) -> bool:
        return EventModel.update(event_id, {"banner_image": filename})

    @staticmethod
    def increment_participants(event_id: str, delta: int = 1) -> bool:
        """Atomically increment (or decrement) current_participants."""
        try:
            result = _col().update_one(
                {"_id": ObjectId(event_id)},
                {
                    "$inc": {"current_participants": delta},
                    "$set": {"updated_at": datetime.now(timezone.utc)},
                },
            )
            return result.modified_count > 0
        except InvalidId:
            return False

    @staticmethod
    def increment_views(event_id: str) -> None:
        try:
            _col().update_one({"_id": ObjectId(event_id)}, {"$inc": {"views": 1}})
        except InvalidId:
            pass

    # ── Delete ────────────────────────────────────────────────────────────────
    @staticmethod
    def delete(event_id: str) -> bool:
        try:
            result = _col().delete_one({"_id": ObjectId(event_id)})
            return result.deleted_count > 0
        except InvalidId:
            return False

    # ── Aggregations ──────────────────────────────────────────────────────────
    @staticmethod
    def count_by_status() -> list:
        pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
        return list(_col().aggregate(pipeline))

    @staticmethod
    def count_by_category() -> list:
        pipeline = [
            {"$group": {"_id": "$category_name", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ]
        return list(_col().aggregate(pipeline))

    @staticmethod
    def monthly_trend(months: int = 6) -> list:
        from datetime import timedelta
        start = datetime.now(timezone.utc) - timedelta(days=months * 30)
        pipeline = [
            {"$match": {"created_at": {"$gte": start}}},
            {"$group": {
                "_id": {"year": {"$year": "$created_at"}, "month": {"$month": "$created_at"}},
                "count": {"$sum": 1},
            }},
            {"$sort": {"_id.year": 1, "_id.month": 1}},
        ]
        return list(_col().aggregate(pipeline))

    # ── Serialization ─────────────────────────────────────────────────────────
    @staticmethod
    def serialize(event: dict) -> dict:
        if not event:
            return {}
        return {
            "id":                   str(event["_id"]),
            "title":                event.get("title"),
            "description":          event.get("description"),
            "category_id":          str(event["category_id"]) if event.get("category_id") else None,
            "category_name":        event.get("category_name"),
            "date":                 event["date"].strftime("%Y-%m-%d") if event.get("date") else None,
            "start_time":           event.get("start_time"),
            "end_time":             event.get("end_time"),
            "location":             event.get("location", {}),
            "location_geo":         event.get("location_geo", None),
            "banner_image":         event.get("banner_image"),
            "max_participants":     event.get("max_participants", 0),
            "current_participants": event.get("current_participants", 0),
            "status":               event.get("status"),
            "created_by":           str(event["created_by"]) if event.get("created_by") else None,
            "tags":                 event.get("tags", []),
            "views":                event.get("views", 0),
            "created_at":           event["created_at"].isoformat() if event.get("created_at") else None,
            "updated_at":           event["updated_at"].isoformat() if event.get("updated_at") else None,
        }
