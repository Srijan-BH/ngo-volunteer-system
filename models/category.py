"""
Category Model — NGO Volunteer Management System
Collection : categories

Schema
------
_id          : ObjectId   (auto)
name         : str        required, unique
slug         : str        required, unique (URL-friendly)
description  : str        optional
icon         : str        CSS class or image filename
color        : str        hex colour for UI badges
is_active    : bool       default True
sort_order   : int        for ordering in UI
created_at   : datetime   auto
updated_at   : datetime   auto

MongoDB JSON Schema Validator included via `get_validator()`.
"""

import logging
import re
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId

from database.connection import get_collection, get_db

logger = logging.getLogger(__name__)

COLLECTION = "categories"


# ─── Helper ───────────────────────────────────────────────────────────────────
def _col():
    return get_collection(COLLECTION)


def _slugify(text: str) -> str:
    """Convert text to a URL-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-")


# ─── MongoDB JSON Schema Validator ────────────────────────────────────────────
def get_validator() -> dict:
    return {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["name", "slug"],
            "additionalProperties": True,
            "properties": {
                "name": {
                    "bsonType": "string",
                    "minLength": 2,
                    "maxLength": 80,
                    "description": "Category name — required, unique",
                },
                "slug": {
                    "bsonType": "string",
                    "pattern": r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
                    "description": "URL-friendly slug — required, unique, lowercase-hyphens",
                },
                "description": {
                    "bsonType": "string",
                    "maxLength": 500,
                    "description": "Short description of the category",
                },
                "icon": {
                    "bsonType": "string",
                    "description": "Bootstrap icon class or image filename",
                },
                "color": {
                    "bsonType": "string",
                    "pattern": r"^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$",
                    "description": "Hex colour code for UI badges e.g. #2563eb",
                },
                "is_active": {
                    "bsonType": "bool",
                    "description": "Whether the category is visible/usable",
                },
                "sort_order": {
                    "bsonType": "int",
                    "minimum": 0,
                    "description": "Display order (ascending)",
                },
                "created_at": {"bsonType": "date"},
                "updated_at": {"bsonType": "date"},
            },
        }
    }


def apply_validator():
    """Apply the JSON schema validator to the categories collection (idempotent)."""
    db = get_db()
    existing = db.list_collection_names()
    if COLLECTION not in existing:
        db.create_collection(COLLECTION, validator=get_validator())
        logger.info(f"Collection '{COLLECTION}' created with validator.")
    else:
        db.command("collMod", COLLECTION, validator=get_validator(), validationLevel="moderate")
        logger.info(f"Validator applied to existing collection '{COLLECTION}'.")


# ─── Model Class ──────────────────────────────────────────────────────────────
class CategoryModel:
    """Static CRUD interface for the `categories` collection."""

    # ── Schema Builder ────────────────────────────────────────────────────────
    @staticmethod
    def build_document(
        name: str,
        description: str = "",
        icon: str = "bi-tag",
        color: str = "#2563eb",
        is_active: bool = True,
        sort_order: int = 0,
        slug: str = None,
    ) -> dict:
        """Build a validated category document (NOT yet saved to DB)."""
        name = name.strip()
        now  = datetime.now(timezone.utc)
        return {
            "name":        name,
            "slug":        slug.strip() if slug else _slugify(name),
            "description": description.strip(),
            "icon":        icon.strip(),
            "color":       color.strip(),
            "is_active":   is_active,
            "sort_order":  int(sort_order),
            "created_at":  now,
            "updated_at":  now,
        }

    # ── Create ────────────────────────────────────────────────────────────────
    @staticmethod
    def create(data: dict) -> str:
        """Insert a new category. Returns inserted _id as string."""
        doc    = CategoryModel.build_document(**data)
        result = _col().insert_one(doc)
        logger.info(f"Category created  id={result.inserted_id}  name='{doc['name']}'")
        return str(result.inserted_id)

    @staticmethod
    def seed_defaults() -> list:
        """
        Insert a set of default NGO categories if the collection is empty.
        Returns list of inserted IDs.
        """
        if _col().count_documents({}) > 0:
            return []

        defaults = [
            {"name": "Education",       "icon": "bi-book",          "color": "#3b82f6", "sort_order": 1},
            {"name": "Health & Medical","icon": "bi-heart-pulse",   "color": "#ef4444", "sort_order": 2},
            {"name": "Environment",     "icon": "bi-tree",          "color": "#10b981", "sort_order": 3},
            {"name": "Community",       "icon": "bi-people",        "color": "#f59e0b", "sort_order": 4},
            {"name": "Disaster Relief", "icon": "bi-life-preserver","color": "#f97316", "sort_order": 5},
            {"name": "Animal Welfare",  "icon": "bi-patch-heart",   "color": "#a855f7", "sort_order": 6},
            {"name": "Women Empowerment","icon":"bi-gender-female",  "color": "#ec4899", "sort_order": 7},
            {"name": "Food & Hunger",   "icon": "bi-bag-heart",     "color": "#84cc16", "sort_order": 8},
            {"name": "Arts & Culture",  "icon": "bi-palette",       "color": "#06b6d4", "sort_order": 9},
            {"name": "Sports",          "icon": "bi-trophy",        "color": "#eab308", "sort_order": 10},
            {"name": "Other",           "icon": "bi-three-dots",    "color": "#64748b", "sort_order": 99},
        ]
        ids = []
        for cat in defaults:
            cid = CategoryModel.create(cat)
            ids.append(cid)
        logger.info(f"Seeded {len(ids)} default categories.")
        return ids

    # ── Read ──────────────────────────────────────────────────────────────────
    @staticmethod
    def find_by_id(category_id: str) -> dict | None:
        try:
            return _col().find_one({"_id": ObjectId(category_id)})
        except InvalidId:
            return None

    @staticmethod
    def find_by_slug(slug: str) -> dict | None:
        return _col().find_one({"slug": slug.strip().lower()})

    @staticmethod
    def find_by_name(name: str) -> dict | None:
        return _col().find_one({"name": {"$regex": f"^{re.escape(name.strip())}$", "$options": "i"}})

    @staticmethod
    def find_all(
        active_only: bool = False,
        sort_by: str = "sort_order",
        sort_order: int = 1,
    ) -> list:
        query = {"is_active": True} if active_only else {}
        return list(_col().find(query).sort(sort_by, sort_order))

    @staticmethod
    def find_active() -> list:
        return CategoryModel.find_all(active_only=True)

    # ── Update ────────────────────────────────────────────────────────────────
    @staticmethod
    def update(category_id: str, update_data: dict) -> bool:
        try:
            update_data["updated_at"] = datetime.now(timezone.utc)
            result = _col().update_one(
                {"_id": ObjectId(category_id)},
                {"$set": update_data},
            )
            return result.modified_count > 0
        except InvalidId:
            return False

    @staticmethod
    def toggle_active(category_id: str) -> bool:
        cat = CategoryModel.find_by_id(category_id)
        if not cat:
            return False
        return CategoryModel.update(category_id, {"is_active": not cat.get("is_active", True)})

    @staticmethod
    def update_sort_order(category_id: str, order: int) -> bool:
        return CategoryModel.update(category_id, {"sort_order": int(order)})

    # ── Delete ────────────────────────────────────────────────────────────────
    @staticmethod
    def delete(category_id: str) -> bool:
        try:
            result = _col().delete_one({"_id": ObjectId(category_id)})
            return result.deleted_count > 0
        except InvalidId:
            return False

    # ── Serialization ─────────────────────────────────────────────────────────
    @staticmethod
    def serialize(cat: dict) -> dict:
        if not cat:
            return {}
        return {
            "id":          str(cat["_id"]),
            "name":        cat.get("name"),
            "slug":        cat.get("slug"),
            "description": cat.get("description", ""),
            "icon":        cat.get("icon", "bi-tag"),
            "color":       cat.get("color", "#2563eb"),
            "is_active":   cat.get("is_active", True),
            "sort_order":  cat.get("sort_order", 0),
            "created_at":  cat["created_at"].isoformat() if cat.get("created_at") else None,
            "updated_at":  cat["updated_at"].isoformat() if cat.get("updated_at") else None,
        }
