"""
Volunteer Controller
Handles volunteer profile management, status updates, skill filtering, and stats.
"""

import logging
from flask import request

from models.volunteer import VolunteerModel, VALID_STATUSES
from models.user import UserModel
from utils.response import success_response, error_response, paginated_response
from utils.pagination import get_pagination_params
from utils.file_upload import save_upload, delete_upload

logger = logging.getLogger(__name__)


class VolunteerController:

    @staticmethod
    def get_all_volunteers(current_user: dict):
        """GET /api/volunteers — List all volunteers with filters and pagination."""
        page, page_size = get_pagination_params(request)
        status = request.args.get("status")
        availability = request.args.get("availability")
        skills = request.args.getlist("skills")
        location = request.args.get("location")

        filters = {}
        if status:
            if status.lower() == "active":
                filters["status"] = {"$in": ["active", "pending"]}
            else:
                filters["status"] = status
        if availability:
            filters["availability"] = availability
        if skills:
            filters["skills"] = {"$in": skills}
        if location:
            filters["location"] = {"$regex": location, "$options": "i"}

        volunteers, total = VolunteerModel.find_all(filters=filters, page=page, page_size=page_size)
        
        serialized = []
        from models.join_request import JoinRequestModel
        for v in volunteers:
            v_data = VolunteerModel.serialize(v)
            user = UserModel.find_by_id(str(v.get("user_id")))
            
            # Compute hours directly from attended events
            v_data["hours_contributed"] = JoinRequestModel.total_hours_by_user(str(v.get("user_id")))
            
            # Default to active if pending (since users are active on signup)
            if v_data.get("status") == "pending":
                v_data["status"] = "active"
                
            if user:
                v_data["user"] = {
                    "name": user.get("full_name"),
                    "email": user.get("email"),
                    "profile_picture": user.get("profile_picture")
                }
            serialized.append(v_data)
            
        return paginated_response(serialized, total, page, page_size)

    @staticmethod
    def get_volunteer(current_user: dict, volunteer_id: str):
        """GET /api/volunteers/<volunteer_id>"""
        volunteer = VolunteerModel.find_by_id(volunteer_id)
        if not volunteer:
            return error_response("Volunteer not found.", 404)
        return success_response(data={"volunteer": VolunteerModel.serialize(volunteer)})

    @staticmethod
    def get_my_profile(current_user: dict):
        """GET /api/volunteers/me — Return the authenticated volunteer's profile."""
        volunteer = VolunteerModel.find_by_user_id(str(current_user["_id"]))
        if not volunteer:
            return error_response("Volunteer profile not found.", 404)
        return success_response(data={"volunteer": VolunteerModel.serialize(volunteer)})

    @staticmethod
    def update_my_profile(current_user: dict):
        """PUT /api/volunteers/me — Update authenticated volunteer's profile."""
        data = request.get_json(silent=True) or {}
        if not data:
            return error_response("No data provided.", 400)

        volunteer = VolunteerModel.find_by_user_id(str(current_user["_id"]))
        if not volunteer:
            return error_response("Volunteer profile not found.", 404)

        allowed = {"bio", "skills", "interests", "availability", "location",
                   "emergency_contact_name", "emergency_contact_phone"}
        update = {}
        for k in allowed:
            if k in data:
                if k == "emergency_contact_name":
                    update.setdefault("emergency_contact", {})["name"] = data[k].strip()
                elif k == "emergency_contact_phone":
                    update.setdefault("emergency_contact", {})["phone"] = data[k].strip()
                else:
                    update[k] = data[k]

        if not update:
            return error_response("No valid fields to update.", 400)

        success = VolunteerModel.update(str(volunteer["_id"]), update)
        if not success:
            return error_response("Failed to update profile.", 500)

        volunteer = VolunteerModel.find_by_id(str(volunteer["_id"]))
        return success_response(
            data={"volunteer": VolunteerModel.serialize(volunteer)},
            message="Profile updated successfully.",
        )

    @staticmethod
    def update_volunteer_status(current_user: dict, volunteer_id: str):
        """PATCH /api/volunteers/<volunteer_id>/status — Admin: change status."""
        data = request.get_json(silent=True) or {}
        status = data.get("status")
        if not status:
            return error_response("Status is required.", 400)
        try:
            success = VolunteerModel.update_status(volunteer_id, status)
            if not success:
                return error_response("Volunteer not found.", 404)
            return success_response(message=f"Volunteer status updated to '{status}'.")
        except ValueError as ve:
            return error_response(str(ve), 400)

    @staticmethod
    def upload_profile_picture(current_user: dict):
        """POST /api/volunteers/me/picture — Upload profile picture."""
        if "file" not in request.files:
            return error_response("No file provided.", 400)

        file = request.files["file"]
        result = save_upload(file, upload_type="profile")
        if not result["success"]:
            return error_response(result["error"], 400)

        # Update user's profile_picture field
        UserModel.update(str(current_user["_id"]), {"profile_picture": result["filename"]})
        return success_response(
            data={"filename": result["filename"], "url": result["url"]},
            message="Profile picture uploaded successfully.",
        )

    @staticmethod
    def get_volunteer_stats(current_user: dict):
        """GET /api/volunteers/stats — Admin: aggregate volunteer statistics."""
        from database.connection import get_db
        db = get_db()

        pipeline = [
            {"$group": {
                "_id": "$status",
                "count": {"$sum": 1},
                "total_hours": {"$sum": "$hours_contributed"},
            }},
        ]
        stats = list(db.volunteers.aggregate(pipeline))
        return success_response(data={"stats": stats})

    @staticmethod
    def export_volunteers(current_user: dict):
        """GET /api/volunteers/export — Admin: export volunteers as CSV."""
        import csv
        import io
        from flask import Response
        
        # Get all volunteers without pagination
        volunteers, _ = VolunteerModel.find_all(page_size=10000)
        
        si = io.StringIO()
        cw = csv.writer(si)
        cw.writerow(['Name', 'Email', 'Status', 'Location', 'Availability', 'Skills', 'Hours Contributed'])
        
        for v in volunteers:
            v_data = VolunteerModel.serialize(v)
            user = UserModel.find_by_id(str(v.get("user_id")))
            name = user.get("full_name", "Unknown") if user else "Unknown"
            email = user.get("email", "Unknown") if user else "Unknown"
            status = v_data.get("status", "pending")
            location = v_data.get("location", "Not set")
            availability = v_data.get("availability", "Flexible")
            skills = ", ".join(v_data.get("skills", []))
            hours = v_data.get("hours_contributed", 0)
            
            cw.writerow([name, email, status, location, availability, skills, hours])
            
        output = si.getvalue()
        return Response(
            output,
            mimetype="text/csv",
            headers={"Content-disposition": "attachment; filename=volunteers_export.csv"}
        )
