from database.connection import init_db, get_db
from flask import Flask
from config.settings import Config

def force_geocode():
    app = Flask(__name__)
    app.config.from_object(Config)
    init_db(app)
    db = get_db()
    
    events = db["events"].find({"location_geo": {"$exists": False}})
    for event in events:
        addr = event.get("location", {}).get("address", "")
        
        if "Panambur" in addr or "Mangalore" in addr or "Mangaluru" in addr:
            print(f"Force updating Mangalore event: {event['title']}")
            db["events"].update_one(
                {"_id": event["_id"]},
                {"$set": {"location_geo": {"type": "Point", "coordinates": [74.8560, 12.9141]}}} # [lng, lat]
            )
        elif "puttur" in addr.lower():
            print(f"Force updating Puttur event: {event['title']}")
            db["events"].update_one(
                {"_id": event["_id"]},
                {"$set": {"location_geo": {"type": "Point", "coordinates": [75.2000, 12.7667]}}} # [lng, lat]
            )
            
    print("Done force updating.")

if __name__ == "__main__":
    force_geocode()
