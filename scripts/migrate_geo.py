import os
import sys

# Add the project root to sys.path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import init_db, get_db
from utils.geocode import geocode_address
from models.event import EventModel
from flask import Flask
from config.settings import Config

def migrate_events_geo():
    app = Flask(__name__)
    app.config.from_object(Config)
    init_db(app)
    db = get_db()
    events_col = db["events"]
    
    events = events_col.find({"location_geo": {"$exists": False}})
    count = 0
    updated = 0
    
    for event in events:
        count += 1
        location = event.get("location", {})
        addr = location.get("address", "")
        venue = location.get("venue", "")
        
        search_str = f"{addr}, {venue}".strip(", ")
        
        if search_str:
            print(f"Geocoding: {search_str}")
            coords = geocode_address(search_str)
            if coords:
                events_col.update_one(
                    {"_id": event["_id"]},
                    {"$set": {"location_geo": {"type": "Point", "coordinates": coords}}}
                )
                updated += 1
                print(f"  -> Success: {coords}")
            else:
                print(f"  -> Failed to find coordinates")
        else:
            print(f"Skipping event {event.get('title')} (no location data)")
            
    print(f"\nMigration complete. Processed {count} events, updated {updated} events.")

if __name__ == "__main__":
    migrate_events_geo()
