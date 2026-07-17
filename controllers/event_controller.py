"""
Event Controller
Handles event creation, listing, search, registration management, and status changes.
"""

import logging
from datetime import datetime, timezone
from flask import request

from models.event import EventModel, VALID_STATUSES, STATUS_PUBLISHED
from models.registration import RegistrationModel, STATUS_CONFIRMED, STATUS_CANCELLED
from models.volunteer import VolunteerModel
from models.notification import NotificationModel, TYPE_REGISTRATION_CONFIRMED, TYPE_EVENT_UPDATED
from utils.response import success_response, error_response, paginated_response
from utils.pagination import get_pagination_params
from utils.validators import validate_required_fields
from utils.file_upload import save_upload

logger = logging.getLogger(__name__)


class EventController:

    @staticmethod
    def get_all_events(current_user: dict = None):
        """GET /api/events — List events with filters and pagination."""
        page, page_size = get_pagination_params(request)
        status = request.args.get("status")
        category = request.args.get("category")
        location = request.args.get("location")
        is_virtual = request.args.get("is_virtual")
        upcoming = request.args.get("upcoming")
        tag = request.args.get("tag")
        lat = request.args.get("lat", type=float)
        lng = request.args.get("lng", type=float)
        radius_miles = request.args.get("radius", type=float)

        filters = {}
        if status:
            filters["status"] = status
        elif current_user is None or current_user.get("role") not in ("admin", "super_admin"):
            # Public API & Volunteers: only show published events
            filters["status"] = STATUS_PUBLISHED
            
        if category:
            filters["category_name"] = category
        if location:
            filters["location.city"] = {"$regex": location, "$options": "i"} # Optional: target specific location fields if needed, or location as string
        if is_virtual is not None:
            filters["location.map_link"] = {"$ne": ""} if is_virtual.lower() in ("true", "1") else "" # Or whatever defines virtual
        if upcoming in ("true", "1"):
            filters["date"] = {"$gte": datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)}
        if tag:
            filters["tags"] = tag
            
        if lat is not None and lng is not None and radius_miles is not None:
            # $nearSphere requires sorting and crashes in countDocuments. 
            # Use $geoWithin with $centerSphere instead. Earth radius is ~3963.2 miles.
            filters["location_geo"] = {
                "$geoWithin": {
                    "$centerSphere": [
                        [lng, lat],
                        radius_miles / 3963.2
                    ]
                }
            }

        events, total = EventModel.find_all(filters=filters, page=page, page_size=page_size)
        serialized = [EventModel.serialize(e) for e in events]
        return paginated_response(serialized, total, page, page_size)

    @staticmethod
    def get_event(event_id: str, current_user: dict = None):
        """GET /api/events/<event_id>"""
        event = EventModel.find_by_id(event_id)
        if not event:
            return error_response("Event not found.", 404)
        EventModel.increment_views(event_id)
        return success_response(data={"event": EventModel.serialize(event)})

    @staticmethod
    def create_event(current_user: dict):
        """POST /api/events — Admin/Staff: create a new event."""
        data = request.get_json(silent=True) or {}

        error = validate_required_fields(data, ["title", "description", "start_date"])
        if error:
            return error_response(error, 400)

        try:
            # Parse dates
            start_date = datetime.fromisoformat(data["start_date"])
            end_date = datetime.fromisoformat(data["end_date"]) if data.get("end_date") else None

            from utils.geocode import geocode_address
            addr = data.get('address', '').strip()
            loc = data.get('location', '').strip()
            if addr and loc and addr.lower() != loc.lower():
                address_str = f"{addr}, {loc}"
            else:
                address_str = addr or loc
            coords = geocode_address(address_str)
            location_geo = {"type": "Point", "coordinates": coords} if coords else None

            event_id = EventModel.create({
                "title": data["title"],
                "description": data["description"],
                "created_by": str(current_user["_id"]),
                "date": start_date,
                "start_time": start_date.strftime("%H:%M"),
                "end_time": end_date.strftime("%H:%M") if end_date else start_date.strftime("%H:%M"),
                "location": {
                    "venue": data.get("location", ""),
                    "address": data.get("address", ""),
                    "map_link": data.get("meeting_link", ""),
                    "geo": location_geo
                },
                "category_name": data.get("category", "other"),
                "max_participants": int(data.get("max_volunteers", 0)),
                "status": data.get("status", "draft"),
                "tags": data.get("skills_required", []),
            })

            event = EventModel.find_by_id(event_id)
            return success_response(
                data={"event": EventModel.serialize(event)},
                message="Event created successfully.",
                status_code=201,
            )
        except ValueError as ve:
            return error_response(str(ve), 400)
        except Exception:
            logger.exception("Create event error")
            return error_response("Failed to create event.", 500)

    @staticmethod
    def update_event(current_user: dict, event_id: str):
        """PUT /api/events/<event_id>"""
        event = EventModel.find_by_id(event_id)
        if not event:
            return error_response("Event not found.", 404)

        data = request.get_json(silent=True) or {}
        allowed = {
            "title", "description", "start_date", "end_date", "location", "address",
            "category", "max_volunteers", "min_volunteers", "status",
            "skills_required", "is_virtual", "meeting_link", "tags", "image",
        }
        update = {k: v for k, v in data.items() if k in allowed}

        for date_field in ("start_date", "end_date"):
            if date_field in update:
                try:
                    update[date_field] = datetime.fromisoformat(update[date_field])
                except ValueError:
                    return error_response(f"Invalid date format for '{date_field}'.", 400)

        # Reconstruct the location object to match MongoDB schema
        if any(k in update for k in ["location", "address", "meeting_link"]):
            current_loc = event.get("location", {})
            venue = update.pop("location", current_loc.get("venue", ""))
            addr = update.pop("address", current_loc.get("address", ""))
            map_link = update.pop("meeting_link", current_loc.get("map_link", ""))
            
            update["location"] = {
                "venue": venue,
                "address": addr,
                "map_link": map_link
            }
            
            from utils.geocode import geocode_address
            addr_str = addr.strip()
            venue_str = venue.strip()
            if addr_str and venue_str and addr_str.lower() != venue_str.lower():
                search_str = f"{addr_str}, {venue_str}"
            else:
                search_str = addr_str or venue_str
            coords = geocode_address(search_str)
            if coords:
                update["location_geo"] = {"type": "Point", "coordinates": coords}

        if not update:
            return error_response("No valid fields to update.", 400)

        EventModel.update(event_id, update)
        updated_event = EventModel.find_by_id(event_id)
        return success_response(
            data={"event": EventModel.serialize(updated_event)},
            message="Event updated successfully.",
        )

    @staticmethod
    def delete_event(current_user: dict, event_id: str):
        """DELETE /api/events/<event_id>"""
        event = EventModel.find_by_id(event_id)
        if not event:
            return error_response("Event not found.", 404)
        EventModel.delete(event_id)
        return success_response(message="Event deleted successfully.")

    @staticmethod
    def get_event_feedback(current_user: dict, event_id: str):
        """GET /api/events/<event_id>/feedback"""
        from models.join_request import JoinRequestModel
        requests, _ = JoinRequestModel.find_by_event(event_id, status="attended", page_size=1000)
        
        feedbacks = []
        total_rating = 0
        count = 0
        
        for req in requests:
            if req.get("rating"):
                feedbacks.append({
                    "rating": req.get("rating"),
                    "feedback": req.get("feedback"),
                    "date": req.get("updated_at").isoformat() if req.get("updated_at") else None
                })
                total_rating += req.get("rating")
                count += 1
                
        avg_rating = round(total_rating / count, 1) if count > 0 else 0
        
        return success_response(data={
            "average_rating": avg_rating,
            "total_reviews": count,
            "feedbacks": feedbacks
        })

    @staticmethod
    def update_event_status(current_user: dict, event_id: str):
        """PATCH /api/events/<event_id>/status"""
        data = request.get_json(silent=True) or {}
        status = data.get("status")
        if not status:
            return error_response("Status is required.", 400)
        try:
            EventModel.update_status(event_id, status)
            return success_response(message=f"Event status updated to '{status}'.")
        except ValueError as ve:
            return error_response(str(ve), 400)

    @staticmethod
    def register_for_event(current_user: dict, event_id: str):
        """POST /api/events/<event_id>/register — Volunteer registers for event."""
        event = EventModel.find_by_id(event_id)
        if not event:
            return error_response("Event not found.", 404)
        if event.get("status") != STATUS_PUBLISHED:
            return error_response("Event is not open for registration.", 400)

        volunteer = VolunteerModel.find_by_user_id(str(current_user["_id"]))
        if not volunteer:
            # Auto-create profile for older accounts that lack one
            try:
                VolunteerModel.create({
                    "user_id": str(current_user["_id"]),
                    "skills": current_user.get("skills", []),
                    "interests": current_user.get("interests", [])
                })
                volunteer = VolunteerModel.find_by_user_id(str(current_user["_id"]))
            except Exception as e:
                logger.error(f"Failed to auto-create volunteer profile: {e}")
                return error_response("Volunteer profile not found and could not be created.", 404)

        volunteer_id = str(volunteer["_id"])

        # Check duplicate registration
        existing = RegistrationModel.find_by_volunteer_and_event(volunteer_id, event_id)
        if existing:
            return error_response("Already registered for this event.", 409)

        # Check capacity
        max_vol = event.get("max_volunteers", 0)
        if max_vol > 0 and event.get("current_volunteers", 0) >= max_vol:
            return error_response("Event is at full capacity.", 400)

        data = request.get_json(silent=True) or {}
        reg_id = RegistrationModel.create(
            volunteer_id=volunteer_id,
            event_id=event_id,
            notes=data.get("notes", ""),
        )
        # Update event stats
        EventModel.increment_participants(event_id)
        
        # Add to volunteer's registered events
        VolunteerModel.update(volunteer_id, {
            "events_registered": volunteer.get("events_registered", []) + [ObjectId(event_id)]
        })

        # Send notification
        NotificationModel.create(
            user_id=str(current_user["_id"]),
            title="Registration Confirmed",
            message=f"You have successfully registered for '{event['title']}'.",
            notification_type=TYPE_REGISTRATION_CONFIRMED,
            related_id=event_id,
            related_model="event",
        )

        registration = RegistrationModel.find_by_id(reg_id)
        return success_response(
            data={"registration": RegistrationModel.serialize(registration)},
            message="Registered for event successfully.",
            status_code=201,
        )

    @staticmethod
    def cancel_registration(current_user: dict, event_id: str):
        """DELETE /api/events/<event_id>/register — Volunteer cancels registration."""
        volunteer = VolunteerModel.find_by_user_id(str(current_user["_id"]))
        if not volunteer:
            return error_response("Volunteer profile not found.", 404)

        reg = RegistrationModel.find_by_volunteer_and_event(str(volunteer["_id"]), event_id)
        if not reg:
            return error_response("Registration not found.", 404)

        RegistrationModel.update_status(str(reg["_id"]), STATUS_CANCELLED)
        EventModel.increment_participants(event_id, delta=-1)

        return success_response(message="Registration cancelled successfully.")

    @staticmethod
    def get_event_registrations(current_user: dict, event_id: str):
        """GET /api/events/<event_id>/registrations — Admin: list registrations."""
        page, page_size = get_pagination_params(request)
        status = request.args.get("status")
        registrations, total = RegistrationModel.find_by_event(event_id, status=status, page=page, page_size=page_size)
        serialized = [RegistrationModel.serialize(r) for r in registrations]
        return paginated_response(serialized, total, page, page_size)

    @staticmethod
    def upload_event_image(current_user: dict, event_id: str):
        """POST /api/events/<event_id>/image"""
        if "file" not in request.files:
            return error_response("No file provided.", 400)

        event = EventModel.find_by_id(event_id)
        if not event:
            return error_response("Event not found.", 404)

        file = request.files["file"]
        result = save_upload(file, upload_type="event")
        if not result["success"]:
            return error_response(result["error"], 400)

        EventModel.update(event_id, {"image": result["filename"]})
        return success_response(
            data={"filename": result["filename"], "url": result["url"]},
            message="Event image uploaded.",
        )

    @staticmethod
    def search_events(current_user: dict = None):
        """GET /api/events/search?q=<query>"""
        query = request.args.get("q", "").strip()
        if not query:
            return error_response("Search query is required.", 400)

        category = request.args.get("category")
        filters = {}
        if category:
            filters["category"] = category
        if current_user is None:
            filters["status"] = STATUS_PUBLISHED

        events = EventModel.search(query, filters)
        serialized = [EventModel.serialize(e) for e in events]
        return success_response(data={"events": serialized, "count": len(serialized)})
