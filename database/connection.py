"""
MongoDB Database Connection Module
Manages the global PyMongo connection and provides access helpers.
"""

import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

logger = logging.getLogger(__name__)

# Global references
_client: MongoClient = None
_db = None


def init_db(app):
    """
    Initialize the MongoDB connection using the Flask app's configuration.
    Sets the global _client and _db references.
    """
    global _client, _db

    mongo_uri = app.config.get("MONGO_URI")
    db_name = app.config.get("MONGO_DBNAME")

    try:
        _client = MongoClient(
            mongo_uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=30000,
            maxPoolSize=50,
            minPoolSize=5,
        )

        # Ping the server to verify connectivity
        _client.admin.command("ping")
        _db = _client[db_name]

        # Setup Collections
        _db.users = _client[db_name]["users"]
        _db.events = _client[db_name]["events"]
        _db.rsvps = _client[db_name]["rsvps"]
        _db.chats = _client[db_name]["chats"]

        logger.info(f"✅ Connected to MongoDB: {db_name}")

        # Store on app for teardown
        app.extensions = getattr(app, "extensions", {})
        app.extensions["mongo_client"] = _client
        app.extensions["mongo_db"] = _db

        # Register teardown
        @app.teardown_appcontext
        def close_db(error=None):
            pass  # Connection pool managed by MongoClient

    except (ConnectionFailure, ServerSelectionTimeoutError) as exc:
        logger.error(f"❌ Could not connect to MongoDB: {exc}")
        raise


def get_db():
    """Return the active database instance."""
    if _db is None:
        raise RuntimeError(
            "Database not initialized. Call init_db(app) first."
        )
    return _db


def get_client():
    """Return the active MongoClient instance."""
    if _client is None:
        raise RuntimeError(
            "Database client not initialized. Call init_db(app) first."
        )
    return _client


def get_collection(collection_name: str):
    """Return a specific collection from the active database."""
    return get_db()[collection_name]


def close_db():
    """Explicitly close the MongoDB connection."""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
        logger.info("MongoDB connection closed.")
