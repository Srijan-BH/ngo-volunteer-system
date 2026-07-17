import os
import sys
import logging
from flask import Flask

# Add the project root to sys.path so we can import from models, database, etc.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.connection import init_db, get_db
from models.admin import AdminModel, ROLE_SUPER_ADMIN
from config.settings import get_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_admin():
    app = Flask(__name__)
    app.config.from_object(get_config())
    init_db(app)

    with app.app_context():
        email = "admin@ngo.org"
        password = "AdminPassword123!"
        
        # Check if exists
        existing = AdminModel.find_by_email(email)
        if existing:
            logger.info(f"Admin '{email}' already exists. Updating password...")
            AdminModel.update_password(str(existing["_id"]), password)
            logger.info("Password updated successfully.")
        else:
            logger.info(f"Creating default admin account '{email}'...")
            admin_id = AdminModel.create({
                "email": email,
                "password": password,
                "role": ROLE_SUPER_ADMIN,
                "name": "Super Admin"
            })
            if admin_id:
                logger.info(f"Admin account created successfully! ID: {admin_id}")
            else:
                logger.error("Failed to create admin account.")

if __name__ == "__main__":
    seed_admin()
