"""
Admin Model — NGO Volunteer Management System
Collection : admins

Schema
------
_id           : ObjectId   (auto)
name          : str        required
email         : str        required, unique, lowercase
password_hash : str        required (bcrypt)
role          : str        enum: super_admin | admin | moderator
is_active     : bool       default True
last_login    : datetime   nullable
created_at    : datetime   auto
updated_at    : datetime   auto

Design note: Admins are stored in a SEPARATE collection from regular users
for clean privilege separation. Super-admins can create/revoke other admins.
"""

import logging
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId

from database.connection import get_collection, get_db
from utils.security import hash_password, verify_password

logger = logging.getLogger(__name__)

COLLECTION = "admins"

# ─── Roles ────────────────────────────────────────────────────────────────────
ROLE_SUPER_ADMIN = "super_admin"
ROLE_ADMIN       = "admin"
ROLE_MODERATOR   = "moderator"
VALID_ROLES      = {ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_MODERATOR}


# ─── Collection accessor ──────────────────────────────────────────────────────
def _col():
    return get_collection(COLLECTION)


# ─── MongoDB JSON Schema Validator ────────────────────────────────────────────
def get_validator() -> dict:
    """Returns the MongoDB $jsonSchema validator for the admins collection."""
    return {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["name", "email", "password_hash", "role"],
            "additionalProperties": True,
            "properties": {
                "name": {
                    "bsonType": "string",
                    "minLength": 2,
                    "maxLength": 100,
                    "description": "Full name of the admin — required",
                },
                "email": {
                    "bsonType": "string",
                    "pattern": r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$",
                    "description": "Admin email — required, unique",
                },
                "password_hash": {
                    "bsonType": "string",
                    "description": "bcrypt hashed password — required",
                },
                "role": {
                    "bsonType": "string",
                    "enum": list(VALID_ROLES),
                    "description": "Admin privilege level — super_admin | admin | moderator",
                },
                "is_active": {
                    "bsonType": "bool",
                    "description": "Whether the admin account is active",
                },
                "last_login": {
                    "bsonType": ["date", "null"],
                    "description": "Timestamp of last successful login",
                },
                "created_at": {
                    "bsonType": "date",
                    "description": "Account creation timestamp",
                },
                "updated_at": {
                    "bsonType": "date",
                    "description": "Last modification timestamp",
                },
            },
        }
    }


def apply_validator():
    """Apply the JSON schema validator to the admins collection (idempotent)."""
    db = get_db()
    existing = db.list_collection_names()
    if COLLECTION not in existing:
        db.create_collection(COLLECTION, validator=get_validator())
        logger.info(f"Collection '{COLLECTION}' created with validator.")
    else:
        db.command("collMod", COLLECTION, validator=get_validator(), validationLevel="moderate")
        logger.info(f"Validator applied to existing collection '{COLLECTION}'.")


# ─── Model Class ──────────────────────────────────────────────────────────────
class AdminModel:
    """Static CRUD interface for the `admins` collection."""

    # ── Schema Builder ────────────────────────────────────────────────────────
    @staticmethod
    def build_document(
        name: str,
        email: str,
        password: str,
        role: str = ROLE_ADMIN,
        is_active: bool = True,
    ) -> dict:
        """
        Build a validated admin document (NOT yet saved to DB).
        Raises ValueError on invalid role.
        """
        if role not in VALID_ROLES:
            raise ValueError(f"Invalid role '{role}'. Choose from: {VALID_ROLES}")

        now = datetime.now(timezone.utc)
        return {
            "name":          name.strip(),
            "email":         email.strip().lower(),
            "password_hash": hash_password(password),
            "role":          role,
            "is_active":     is_active,
            "last_login":    None,
            "created_at":    now,
            "updated_at":    now,
        }

    # ── Create ────────────────────────────────────────────────────────────────
    @staticmethod
    def create(data: dict) -> str:
        """Insert a new admin document. Returns inserted _id as string."""
        doc    = AdminModel.build_document(**data)
        result = _col().insert_one(doc)
        logger.info(f"Admin created  id={result.inserted_id}  email={doc['email']}  role={doc['role']}")
        return str(result.inserted_id)

    # ── Read (single) ─────────────────────────────────────────────────────────
    @staticmethod
    def find_by_id(admin_id: str) -> dict | None:
        try:
            return _col().find_one({"_id": ObjectId(admin_id)})
        except InvalidId:
            return None

    @staticmethod
    def find_by_email(email: str) -> dict | None:
        return _col().find_one({"email": email.strip().lower()})

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
    def find_by_role(role: str) -> list:
        return list(_col().find({"role": role}))

    @staticmethod
    def find_active() -> list:
        return list(_col().find({"is_active": True}))

    # ── Update ────────────────────────────────────────────────────────────────
    @staticmethod
    def update(admin_id: str, update_data: dict) -> bool:
        try:
            update_data["updated_at"] = datetime.now(timezone.utc)
            result = _col().update_one(
                {"_id": ObjectId(admin_id)},
                {"$set": update_data},
            )
            return result.modified_count > 0
        except InvalidId:
            return False

    @staticmethod
    def update_password(admin_id: str, new_password: str) -> bool:
        return AdminModel.update(admin_id, {"password_hash": hash_password(new_password)})

    @staticmethod
    def update_role(admin_id: str, new_role: str) -> bool:
        if new_role not in VALID_ROLES:
            raise ValueError(f"Invalid role '{new_role}'.")
        return AdminModel.update(admin_id, {"role": new_role})

    @staticmethod
    def update_last_login(admin_id: str) -> None:
        AdminModel.update(admin_id, {"last_login": datetime.now(timezone.utc)})

    @staticmethod
    def deactivate(admin_id: str) -> bool:
        return AdminModel.update(admin_id, {"is_active": False})

    @staticmethod
    def activate(admin_id: str) -> bool:
        return AdminModel.update(admin_id, {"is_active": True})

    # ── Delete ────────────────────────────────────────────────────────────────
    @staticmethod
    def delete(admin_id: str) -> bool:
        try:
            result = _col().delete_one({"_id": ObjectId(admin_id)})
            return result.deleted_count > 0
        except InvalidId:
            return False

    # ── Auth Helper ───────────────────────────────────────────────────────────
    @staticmethod
    def verify_credentials(email: str, password: str) -> dict | None:
        """Return the admin doc if credentials are valid, else None."""
        admin = AdminModel.find_by_email(email)
        if not admin:
            return None
        if not admin.get("is_active"):
            return None
        if not verify_password(password, admin.get("password_hash", "")):
            return None
        return admin

    # ── Privilege Checks ──────────────────────────────────────────────────────
    @staticmethod
    def is_super_admin(admin_id: str) -> bool:
        admin = AdminModel.find_by_id(admin_id)
        return admin is not None and admin.get("role") == ROLE_SUPER_ADMIN

    @staticmethod
    def can_manage_users(admin: dict) -> bool:
        return admin.get("role") in {ROLE_SUPER_ADMIN, ROLE_ADMIN}

    @staticmethod
    def can_manage_events(admin: dict) -> bool:
        return admin.get("role") in {ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_MODERATOR}

    # ── Serialization ─────────────────────────────────────────────────────────
    @staticmethod
    def serialize(admin: dict, include_sensitive: bool = False) -> dict:
        """Convert a MongoDB document to a JSON-safe dict."""
        if not admin:
            return {}
        out = {
            "id":         str(admin["_id"]),
            "name":       admin.get("name"),
            "email":      admin.get("email"),
            "role":       admin.get("role"),
            "is_active":  admin.get("is_active", True),
            "last_login": admin["last_login"].isoformat() if admin.get("last_login") else None,
            "created_at": admin["created_at"].isoformat() if admin.get("created_at") else None,
            "updated_at": admin["updated_at"].isoformat() if admin.get("updated_at") else None,
        }
        if include_sensitive:
            out["password_hash"] = admin.get("password_hash")
        return out
