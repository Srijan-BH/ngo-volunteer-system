import os
import sys

# Add the project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import init_db
from models.join_request import apply_validator
from flask import Flask
from config.settings import Config

def update_db_schema():
    app = Flask(__name__)
    app.config.from_object(Config)
    init_db(app)
    
    print("Applying validator to join_requests collection...")
    apply_validator()
    print("Successfully updated database schema for Feedback & Ratings!")

if __name__ == "__main__":
    update_db_schema()
