"""
Password Reset Model — NGO Volunteer Management System
Collection : password_resets

Schema
------
_id        : ObjectId   (auto)
entity_id  : ObjectId   ref → users._id or admins._id
entity     : str        "user" | "admin"
token_hash : str        SHA-256 hash of the raw reset token (never store raw)
jti        : str        JWT ID — used to blacklist after single-use
is_used    : bool       True once the reset is consumed
expires_at : datetime   15 minutes from creation
created_at : datetime   auto (also TTL index — auto-delete after 24 h)

Security model:
  1. A 15-minute JWT is generated and emailed to the user.
  2. We store only the token's JTI + SHA-256 hash (never the raw token).
  3. On redemption: verify JWT → look up JTI → mark is_used=True → blacklist JTI.
  4. The TTL index removes stale records after 24 hours automatically.
"""

import hashlib
import logging
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from bson.errors import InvalidId

from database.connection import get_collection, get_db

logger = logging.getLogger(__name__)

COLLECTION = "password_resets"


# ─── Helper ───────────────────────────────────────────────────────────────────
def _col():
    return get_collection(COLLECTION)


def _hash_token(token: str) -> str:
    """Return SHA-256 hex digest of a token string."""
    return hashlib.sha256(token.encode()).hexdigest()


# ─── MongoDB JSON Schema Validator ────────────────────────────────────────────
def get_validator() -> dict:
    return {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["entity_id", "entity", "token_hash", "jti", "expires_at"],
            "additionalProperties": True,
            "properties": {
                "entity_id":  {"bsonType": "objectId"},
                "entity":     {"bsonType": "string", "enum": ["user", "admin"]},
                "token_hash": {"bsonType": "string"},
                "jti":        {"bsonType": "string"},
                "is_used":    {"bsonType": "bool"},
                "expires_at": {"bsonType": "date"},
                "created_at": {"bsonType": "date"},
            },
        }
    }


def apply_validator():
    """Apply the JSON schema validator (idempotent)."""
    db = get_db()
    if COLLECTION not in db.list_collection_names():
        db.create_collection(COLLECTION, validator=get_validator())
        logger.info(f"Collection '{COLLECTION}' created with validator.")
    else:
        db.command("collMod", COLLECTION, validator=get_validator(), validationLevel="moderate")
        logger.info(f"Validator applied to existing '{COLLECTION}'.")


# ─── Model Class ──────────────────────────────────────────────────────────────
class PasswordResetModel:
    """Manages one-time password-reset tokens."""

    @staticmethod
    def create(entity_id: str, entity: str, raw_token: str, jti: str) -> str:
        """
        Store a password reset record.

        Args:
            entity_id:  User or admin _id string.
            entity:     "user" | "admin".
            raw_token:  The raw JWT (we only store its hash).
            jti:        The JWT's JTI claim.

        Returns:
            Inserted document _id as string.
        """
        now = datetime.now(timezone.utc)
        doc = {
            "entity_id":  ObjectId(entity_id),
            "entity":     entity,
            "token_hash": _hash_token(raw_token),
            "jti":        jti,
            "is_used":    False,
            "expires_at": now + timedelta(minutes=15),
            "created_at": now,
        }
        # Invalidate any prior unused requests for this entity
        _col().update_many(
            {"entity_id": ObjectId(entity_id), "entity": entity, "is_used": False},
            {"$set": {"is_used": True}},
        )
        result = _col().insert_one(doc)
        logger.info(f"Password reset record created for {entity} {entity_id}")
        return str(result.inserted_id)

    @staticmethod
    def find_by_jti(jti: str) -> dict | None:
        return _col().find_one({"jti": jti})

    @staticmethod
    def is_valid(jti: str, raw_token: str) -> bool:
        """
        Return True if the JTI maps to an unused, non-expired record
        whose token hash matches.
        """
        record = PasswordResetModel.find_by_jti(jti)
        if not record:
            return False
        if record.get("is_used"):
            return False
        if record.get("expires_at") < datetime.now(timezone.utc):
            return False
        if record.get("token_hash") != _hash_token(raw_token):
            return False
        return True

    @staticmethod
    def consume(jti: str) -> bool:
        """Mark the reset token as used (one-time use)."""
        result = _col().update_one(
            {"jti": jti},
            {"$set": {"is_used": True}},
        )
        return result.modified_count > 0

    @staticmethod
    def invalidate_all_for_entity(entity_id: str, entity: str) -> int:
        """Invalidate all pending reset tokens for a given entity (security measure)."""
        try:
            result = _col().update_many(
                {"entity_id": ObjectId(entity_id), "entity": entity, "is_used": False},
                {"$set": {"is_used": True}},
            )
            return result.modified_count
        except InvalidId:
            return 0
