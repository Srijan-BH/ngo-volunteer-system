"""
User Model — NGO Volunteer Management System
Collection : users

Schema
------
_id             : ObjectId   (auto)
full_name       : str        required
email           : str        required, unique, lowercase
mobile          : str        required
password_hash   : str        required (bcrypt)
skills          : list[str]  default []
interests       : list[str]  default []
address         : dict       { street, city, state, country, pincode }
profile_image   : str        filename (relative URL)
role            : str        enum: volunteer | staff | admin
status          : str        enum: active | inactive | suspended | pending
email_verified  : bool       default False
last_login      : datetime   nullable
created_at      : datetime   auto
updated_at      : datetime   auto

MongoDB JSON Schema Validator included via `get_validator()`.
"""

import logging
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId

from database.connection import get_collection, get_db
from utils.security import hash_password, verify_password

logger = logging.getLogger(__name__)

COLLECTION = "users"

# ─── Enums ────────────────────────────────────────────────────────────────────
ROLE_VOLUNTEER = "volunteer"
ROLE_STAFF     = "staff"
ROLE_ADMIN     = "admin"
VALID_ROLES    = {ROLE_VOLUNTEER, ROLE_STAFF, ROLE_ADMIN}

STATUS_ACTIVE    = "active"
STATUS_INACTIVE  = "inactive"
STATUS_SUSPENDED = "suspended"
STATUS_PENDING   = "pending"
VALID_STATUSES   = {STATUS_ACTIVE, STATUS_INACTIVE, STATUS_SUSPENDED, STATUS_PENDING}


# ─── Collection accessor ──────────────────────────────────────────────────────
def _col():
    return get_collection(COLLECTION)


# ─── MongoDB JSON Schema Validator ────────────────────────────────────────────
def get_validator() -> dict:
    """
    Returns the MongoDB $jsonSchema validator for the users collection.
    Apply once via db.create_collection() or db.command('collMod').
    """
    return {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["full_name", "email", "mobile", "password_hash", "role", "status"],
            "additionalProperties": True,
            "properties": {
                "full_name": {
                    "bsonType": "string",
                    "minLength": 2,
                    "maxLength": 120,
                    "description": "Full name of the volunteer — required string",
                },
                "email": {
                    "bsonType": "string",
                    "pattern": r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$",
                    "description": "Valid email address — required, unique",
                },
                "mobile": {
                    "bsonType": "string",
                    "pattern": r"^\+?[0-9]{7,15}$",
                    "description": "Mobile number — required",
                },
                "password_hash": {
                    "bsonType": "string",
                    "description": "bcrypt password hash — required",
                },
                "skills": {
                    "bsonType": "array",
                    "items": {"bsonType": "string"},
                    "description": "List of skills",
                },
                "interests": {
                    "bsonType": "array",
                    "items": {"bsonType": "string"},
                    "description": "List of interests / causes",
                },
                "address": {
                    "bsonType": "object",
                    "properties": {
                        "street":  {"bsonType": "string"},
                        "city":    {"bsonType": "string"},
                        "state":   {"bsonType": "string"},
                        "country": {"bsonType": "string"},
                        "pincode": {"bsonType": "string"},
                    },
                    "description": "Structured address",
                },
                "profile_image": {
                    "bsonType": "string",
                    "description": "Stored filename / relative URL of profile image",
                },
                "role": {
                    "bsonType": "string",
                    "enum": list(VALID_ROLES),
                    "description": "User role — volunteer | staff | admin",
                },
                "status": {
                    "bsonType": "string",
                    "enum": list(VALID_STATUSES),
                    "description": "Account status — active | inactive | suspended | pending",
                },
                "email_verified": {"bsonType": "bool"},
                "last_login":     {"bsonType": ["date", "null"]},
                "created_at":     {"bsonType": "date"},
                "updated_at":     {"bsonType": "date"},
            },
        }
    }


def apply_validator():
    """Apply the JSON schema validator to the collection (idempotent)."""
    db = get_db()
    existing = db.list_collection_names()
    if COLLECTION not in existing:
        db.create_collection(COLLECTION, validator=get_validator())
        logger.info(f"Collection '{COLLECTION}' created with validator.")
    else:
        db.command("collMod", COLLECTION, validator=get_validator(), validationLevel="moderate")
        logger.info(f"Validator applied to existing collection '{COLLECTION}'.")


# ─── Model Class ──────────────────────────────────────────────────────────────
class UserModel:
    """Static CRUD interface for the `users` collection."""

    # ── Schema Builder ────────────────────────────────────────────────────────
    @staticmethod
    def build_document(
        full_name: str,
        email: str,
        mobile: str,
        password: str,
        role: str = ROLE_VOLUNTEER,
        status: str = STATUS_PENDING,
        skills: list = None,
        interests: list = None,
        address: dict = None,
        profile_image: str = "",
    ) -> dict:
        """
        Build a validated user document (NOT yet saved to DB).
        Raises ValueError on invalid role/status.
        """
        if role not in VALID_ROLES:
            raise ValueError(f"Invalid role '{role}'. Choose from: {VALID_ROLES}")
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{status}'. Choose from: {VALID_STATUSES}")

        now = datetime.now(timezone.utc)
        return {
            "full_name":      full_name.strip(),
            "email":          email.strip().lower(),
            "mobile":         mobile.strip(),
            "password_hash":  hash_password(password),
            "skills":         [s.strip() for s in (skills or [])],
            "interests":      [i.strip() for i in (interests or [])],
            "address": {
                "street":  (address or {}).get("street", "").strip(),
                "city":    (address or {}).get("city", "").strip(),
                "state":   (address or {}).get("state", "").strip(),
                "country": (address or {}).get("country", "").strip(),
                "pincode": (address or {}).get("pincode", "").strip(),
            },
            "profile_image":  profile_image.strip(),
            "role":           role,
            "status":         status,
            "email_verified": False,
            "last_login":     None,
            "created_at":     now,
            "updated_at":     now,
        }

    # ── Create ────────────────────────────────────────────────────────────────
    @staticmethod
    def create(data: dict) -> str:
        """Insert a new user document. Returns inserted _id as string."""
        doc = UserModel.build_document(**data)
        result = _col().insert_one(doc)
        logger.info(f"User created  id={result.inserted_id}  email={doc['email']}")
        return str(result.inserted_id)

    # ── Read (single) ─────────────────────────────────────────────────────────
    @staticmethod
    def find_by_id(user_id: str) -> dict | None:
        try:
            return _col().find_one({"_id": ObjectId(user_id)})
        except InvalidId:
            return None

    @staticmethod
    def find_by_email(email: str) -> dict | None:
        return _col().find_one({"email": email.strip().lower()})

    @staticmethod
    def find_by_mobile(mobile: str) -> dict | None:
        return _col().find_one({"mobile": mobile.strip()})

    # ── Read (list) ───────────────────────────────────────────────────────────
    @staticmethod
    def find_all(
        filters: dict = None,
        page: int = 1,
        page_size: int = 10,
        sort_by: str = "created_at",
        sort_order: int = -1,
    ) -> tuple[list, int]:
        """Return (list_of_docs, total_count) with pagination."""
        query = filters or {}
        col   = _col()
        total = col.count_documents(query)
        skip  = (page - 1) * page_size
        docs  = list(col.find(query).sort(sort_by, sort_order).skip(skip).limit(page_size))
        return docs, total

    @staticmethod
    def find_by_role(
        role: str,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list, int]:
        return UserModel.find_all({"role": role}, page, page_size)

    @staticmethod
    def find_by_status(
        status: str,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list, int]:
        return UserModel.find_all({"status": status}, page, page_size)

    @staticmethod
    def find_by_skills(skills: list) -> list:
        """Return all volunteers that have ANY of the given skills."""
        return list(_col().find({"skills": {"$in": skills}}))

    @staticmethod
    def search(query_str: str, page: int = 1, page_size: int = 10) -> tuple[list, int]:
        """Search users by full_name, email, or mobile (regex)."""
        regex = {"$regex": query_str, "$options": "i"}
        filt  = {"$or": [{"full_name": regex}, {"email": regex}, {"mobile": regex}]}
        return UserModel.find_all(filt, page, page_size)

    # ── Update ────────────────────────────────────────────────────────────────
    @staticmethod
    def update(user_id: str, update_data: dict) -> bool:
        try:
            update_data["updated_at"] = datetime.now(timezone.utc)
            result = _col().update_one(
                {"_id": ObjectId(user_id)},
                {"$set": update_data},
            )
            return result.modified_count > 0
        except InvalidId:
            return False

    @staticmethod
    def update_password(user_id: str, new_password: str) -> bool:
        return UserModel.update(user_id, {"password_hash": hash_password(new_password)})

    @staticmethod
    def update_status(user_id: str, status: str) -> bool:
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{status}'.")
        return UserModel.update(user_id, {"status": status})

    @staticmethod
    def update_profile_image(user_id: str, filename: str) -> bool:
        return UserModel.update(user_id, {"profile_image": filename})

    @staticmethod
    def update_last_login(user_id: str) -> None:
        UserModel.update(user_id, {"last_login": datetime.now(timezone.utc)})

    @staticmethod
    def verify_email(user_id: str) -> bool:
        return UserModel.update(user_id, {"email_verified": True})

    # ── Delete ────────────────────────────────────────────────────────────────
    @staticmethod
    def soft_delete(user_id: str) -> bool:
        """Deactivate user (status = inactive)."""
        return UserModel.update_status(user_id, STATUS_INACTIVE)

    @staticmethod
    def hard_delete(user_id: str) -> bool:
        try:
            result = _col().delete_one({"_id": ObjectId(user_id)})
            return result.deleted_count > 0
        except InvalidId:
            return False

    # ── Auth Helper ───────────────────────────────────────────────────────────
    @staticmethod
    def verify_credentials(email: str, password: str) -> dict | None:
        """Return the user doc if credentials are valid, else None."""
        user = UserModel.find_by_email(email)
        if not user:
            return None
        if not verify_password(password, user.get("password_hash", "")):
            return None
        return user

    # ── Aggregations ──────────────────────────────────────────────────────────
    @staticmethod
    def count_by_status() -> list:
        pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
        return list(_col().aggregate(pipeline))

    @staticmethod
    def count_by_role() -> list:
        pipeline = [{"$group": {"_id": "$role", "count": {"$sum": 1}}}]
        return list(_col().aggregate(pipeline))

    @staticmethod
    def top_skills(limit: int = 20) -> list:
        pipeline = [
            {"$unwind": "$skills"},
            {"$group": {"_id": "$skills", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": limit},
        ]
        return list(_col().aggregate(pipeline))

    # ── Serialization ─────────────────────────────────────────────────────────
    @staticmethod
    def serialize(user: dict, include_sensitive: bool = False) -> dict:
        """Convert a MongoDB document to a JSON-safe dict."""
        if not user:
            return {}
        out = {
            "id":            str(user["_id"]),
            "full_name":     user.get("full_name"),
            "email":         user.get("email"),
            "mobile":        user.get("mobile"),
            "skills":        user.get("skills", []),
            "interests":     user.get("interests", []),
            "address":       user.get("address", {}),
            "profile_image": user.get("profile_image"),
            "role":          user.get("role"),
            "status":        user.get("status"),
            "email_verified": user.get("email_verified", False),
            "last_login":    user["last_login"].isoformat() if user.get("last_login") else None,
            "created_at":    user["created_at"].isoformat() if user.get("created_at") else None,
            "updated_at":    user["updated_at"].isoformat() if user.get("updated_at") else None,
        }
        if include_sensitive:
            out["password_hash"] = user.get("password_hash")
        return out
