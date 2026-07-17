"""
Database Indexes Setup — NGO Volunteer Management System
Defines all MongoDB indexes for optimal query performance.

Collections covered:
  users · admins · events · categories · join_requests · notifications · token_blacklist

Run once at startup or migration:
    python -m database.indexes
"""

import logging
from pymongo import ASCENDING, DESCENDING, TEXT, IndexModel
from database.connection import get_db

logger = logging.getLogger(__name__)


def create_indexes():
    """Create all required MongoDB indexes across every collection."""
    db = get_db()

    # ─── users ────────────────────────────────────────────────────────────────
    db.users.create_indexes([
        IndexModel([("email",  ASCENDING)], unique=True,  name="idx_users_email_unique"),
        IndexModel([("mobile", ASCENDING)], unique=True,  name="idx_users_mobile_unique"),
        IndexModel([("role",   ASCENDING)],               name="idx_users_role"),
        IndexModel([("status", ASCENDING)],               name="idx_users_status"),
        IndexModel([("skills", ASCENDING)],               name="idx_users_skills"),
        IndexModel([("interests", ASCENDING)],            name="idx_users_interests"),
        IndexModel([("created_at", DESCENDING)],          name="idx_users_created_at"),
        # Text search across name + email
        IndexModel(
            [("full_name", TEXT), ("email", TEXT)],
            name="idx_users_text_search",
        ),
    ])
    logger.info("✅ users indexes created.")

    # ─── admins ───────────────────────────────────────────────────────────────
    db.admins.create_indexes([
        IndexModel([("email",    ASCENDING)], unique=True, name="idx_admins_email_unique"),
        IndexModel([("role",     ASCENDING)],              name="idx_admins_role"),
        IndexModel([("is_active",ASCENDING)],              name="idx_admins_is_active"),
        IndexModel([("created_at",DESCENDING)],            name="idx_admins_created_at"),
    ])
    logger.info("✅ admins indexes created.")

    # ─── categories ───────────────────────────────────────────────────────────
    db.categories.create_indexes([
        IndexModel([("slug",       ASCENDING)], unique=True, name="idx_categories_slug_unique"),
        IndexModel([("name",       ASCENDING)], unique=True, name="idx_categories_name_unique"),
        IndexModel([("is_active",  ASCENDING)],              name="idx_categories_is_active"),
        IndexModel([("sort_order", ASCENDING)],              name="idx_categories_sort_order"),
    ])
    logger.info("✅ categories indexes created.")

    # ─── events ───────────────────────────────────────────────────────────────
    db.events.create_indexes([
        # Full-text search
        IndexModel(
            [("title", TEXT), ("description", TEXT), ("tags", TEXT)],
            name="idx_events_text_search",
            weights={"title": 10, "tags": 5, "description": 1},
        ),
        IndexModel([("status",      ASCENDING)],  name="idx_events_status"),
        IndexModel([("category_id", ASCENDING)],  name="idx_events_category_id"),
        IndexModel([("date",        ASCENDING)],  name="idx_events_date"),
        IndexModel([("created_by",  ASCENDING)],  name="idx_events_created_by"),
        IndexModel([("created_at",  DESCENDING)], name="idx_events_created_at"),
        # Compound: date + status for upcoming-events queries
        IndexModel(
            [("date", ASCENDING), ("status", ASCENDING)],
            name="idx_events_date_status",
        ),
        # 2dsphere index for geolocation queries
        IndexModel([("location_geo", "2dsphere")], name="idx_events_location_geo"),
    ])
    logger.info("✅ events indexes created.")

    # ─── join_requests ────────────────────────────────────────────────────────
    db.join_requests.create_indexes([
        # Unique: one request per user per event
        IndexModel(
            [("user_id", ASCENDING), ("event_id", ASCENDING)],
            unique=True,
            name="idx_joinreq_user_event_unique",
        ),
        IndexModel([("event_id",    ASCENDING)],  name="idx_joinreq_event_id"),
        IndexModel([("user_id",     ASCENDING)],  name="idx_joinreq_user_id"),
        IndexModel([("status",      ASCENDING)],  name="idx_joinreq_status"),
        IndexModel([("applied_date",DESCENDING)], name="idx_joinreq_applied_date"),
        IndexModel([("reviewed_by", ASCENDING)],  name="idx_joinreq_reviewed_by"),
        # Compound: event + status for admin review queries
        IndexModel(
            [("event_id", ASCENDING), ("status", ASCENDING)],
            name="idx_joinreq_event_status",
        ),
    ])
    logger.info("✅ join_requests indexes created.")

    # ─── notifications ────────────────────────────────────────────────────────
    db.notifications.create_indexes([
        IndexModel([("user_id",   ASCENDING)],  name="idx_notif_user_id"),
        IndexModel([("is_read",   ASCENDING)],  name="idx_notif_is_read"),
        IndexModel([("type",      ASCENDING)],  name="idx_notif_type"),
        IndexModel([("created_at",DESCENDING)], name="idx_notif_created_at"),
        # Compound: user + is_read for unread count queries
        IndexModel(
            [("user_id", ASCENDING), ("is_read", ASCENDING)],
            name="idx_notif_user_is_read",
        ),
        # Compound: user + related_id for contextual lookup
        IndexModel(
            [("user_id", ASCENDING), ("related_id", ASCENDING)],
            name="idx_notif_user_related",
        ),
        # TTL: auto-delete notifications older than 90 days
        IndexModel(
            [("created_at", ASCENDING)],
            expireAfterSeconds=7_776_000,   # 90 days
            name="idx_notif_ttl_90days",
        ),
    ])
    logger.info("✅ notifications indexes created.")

    # ─── password_resets ──────────────────────────────────────────────────────
    db.password_resets.create_indexes([
        IndexModel([("jti",       ASCENDING)], unique=True, name="idx_pwdreset_jti_unique"),
        IndexModel([("entity_id", ASCENDING)],              name="idx_pwdreset_entity_id"),
        IndexModel([("is_used",   ASCENDING)],              name="idx_pwdreset_is_used"),
        # TTL: auto-delete reset records after 24 hours
        IndexModel(
            [("created_at", ASCENDING)],
            expireAfterSeconds=86_400,      # 24 hours
            name="idx_pwdreset_ttl_24h",
        ),
    ])
    logger.info("✅ password_resets indexes created.")

    # ─── token_blacklist ──────────────────────────────────────────────────────
    db.token_blacklist.create_indexes([
        IndexModel([("jti", ASCENDING)], unique=True, name="idx_tokenbl_jti_unique"),
        # TTL: auto-delete blacklist entries after 90 days
        IndexModel(
            [("blacklisted_at", ASCENDING)],
            expireAfterSeconds=7_776_000,   # 90 days
            name="idx_tokenbl_ttl_90days",
        ),
    ])
    logger.info("✅ token_blacklist indexes created.")

    logger.info("🎉 All database indexes created successfully.")


def apply_collection_validators():
    """Apply MongoDB JSON Schema validators to all collections."""
    from models.user           import apply_validator as user_validator
    from models.admin          import apply_validator as admin_validator
    from models.category       import apply_validator as category_validator
    from models.event          import apply_validator as event_validator
    from models.join_request   import apply_validator as joinreq_validator
    from models.notification   import apply_validator as notif_validator
    from models.password_reset import apply_validator as pwdreset_validator

    user_validator()
    admin_validator()
    category_validator()
    event_validator()
    joinreq_validator()
    notif_validator()
    pwdreset_validator()

    logger.info("🎉 All collection validators applied successfully.")


def setup_database():
    """Full database setup: validators + indexes."""
    apply_collection_validators()
    create_indexes()


if __name__ == "__main__":
    # Run standalone: python -m database.indexes
    from app import create_app
    app = create_app()
    with app.app_context():
        setup_database()
