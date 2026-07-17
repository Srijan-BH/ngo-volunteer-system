"""
API Routes for Volunteer Requests
Endpoints under /api/requests (user) and /api/admin/requests (admin)
"""

from flask import Blueprint, request, jsonify, g
from middleware.auth_middleware import require_user_auth, require_admin_auth
from controllers.request_controller import RequestController

request_bp = Blueprint("request_bp", __name__)

# ─── USER ENDPOINTS ───────────────────────────────────────────────────────────

@request_bp.route("/api/requests", methods=["POST"])
@require_user_auth
def apply_for_event(current_user):
    """User applies for an event."""
    data = request.get_json() or {}
    
    event_id = data.get("event_id")
    user_remarks = data.get("user_remarks", "")
    
    if not event_id:
        return jsonify({"status": "error", "message": "event_id is required"}), 400
        
    success, message, result = RequestController.apply_for_event(str(current_user["_id"]), event_id, user_remarks)
    
    if success:
        return jsonify({"status": "success", "message": message, "data": result}), 201
    else:
        return jsonify({"status": "error", "message": message}), 400

@request_bp.route("/api/requests/my-requests", methods=["GET"])
@require_user_auth
def my_requests(current_user):
    """Get all requests for the currently logged-in user."""
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 10))
    status = request.args.get("status")
    
    requests, total = RequestController.get_user_requests(str(current_user["_id"]), status, page, page_size)
    
    return jsonify({
        "status": "success",
        "data": requests,
        "meta": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size
        }
    }), 200

@request_bp.route("/api/requests/<request_id>/withdraw", methods=["POST"])
@require_user_auth
def withdraw_request(current_user, request_id):
    """User withdraws their own request."""
    success, message = RequestController.withdraw_request(str(current_user["_id"]), request_id)
    
    if success:
        return jsonify({"status": "success", "message": message}), 200
    else:
        return jsonify({"status": "error", "message": message}), 400

@request_bp.route("/api/requests/<request_id>/certificate", methods=["GET"])
@require_user_auth
def get_certificate_data(current_user, request_id):
    """Get data for a volunteer's certificate."""
    success, message, data = RequestController.get_certificate_data(str(current_user["_id"]), request_id)
    if success:
        return jsonify({"status": "success", "data": data}), 200
    else:
        return jsonify({"status": "error", "message": message}), 400

@request_bp.route("/api/requests/<request_id>/feedback", methods=["POST"])
@require_user_auth
def submit_feedback(current_user, request_id):
    """User submits rating and feedback for an attended event."""
    data = request.get_json() or {}
    rating = data.get("rating")
    feedback = data.get("feedback", "")
    
    if not rating:
        return jsonify({"status": "error", "message": "Rating is required"}), 400
        
    success, message = RequestController.submit_feedback(str(current_user["_id"]), request_id, rating, feedback)
    
    if success:
        return jsonify({"status": "success", "message": message}), 200
    else:
        return jsonify({"status": "error", "message": message}), 400


# ─── ADMIN ENDPOINTS ──────────────────────────────────────────────────────────

@request_bp.route("/api/admin/requests", methods=["GET"])
@require_admin_auth
def get_admin_requests(current_admin):
    """Admin gets all requests, optionally filtered by status."""
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 10))
    status = request.args.get("status")
    
    requests, total = RequestController.get_all_requests(status, page, page_size)
    
    return jsonify({
        "status": "success",
        "data": requests,
        "meta": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size
        }
    }), 200

@request_bp.route("/api/admin/requests/pending", methods=["GET"])
@require_admin_auth
def get_pending_requests(current_admin):
    """Admin gets all pending requests (Legacy Endpoint)."""
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 10))
    
    requests, total = RequestController.get_pending_requests(page, page_size)
    
    return jsonify({
        "status": "success",
        "data": requests,
        "meta": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size
        }
    }), 200

@request_bp.route("/api/admin/requests/<request_id>/attended", methods=["POST"])
@require_admin_auth
def mark_request_attended(current_admin, request_id):
    """Admin marks a request as attended and logs hours."""
    data = request.get_json() or {}
    try:
        hours = float(data.get("hours", 0.0))
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid hours value."}), 400
        
    success, message = RequestController.mark_request_attended(str(current_admin["_id"]), request_id, hours)
    
    if success:
        return jsonify({"status": "success", "message": message}), 200
    else:
        return jsonify({"status": "error", "message": message}), 400

@request_bp.route("/api/admin/events/<event_id>/requests", methods=["GET"])
@require_admin_auth
def get_event_requests(current_admin, event_id):
    """Admin gets all requests for a specific event."""
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 10))
    status = request.args.get("status") # Optional filter
    
    requests, total = RequestController.get_event_requests(event_id, status, page, page_size)
    
    return jsonify({
        "status": "success",
        "data": requests,
        "meta": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size
        }
    }), 200

@request_bp.route("/api/admin/requests/<request_id>/approve", methods=["POST"])
@require_admin_auth
def approve_request(current_admin, request_id):
    """Admin approves a request."""
    data = request.get_json() or {}
    remarks = data.get("remarks", "")
    
    success, message = RequestController.approve_request(str(current_admin["_id"]), request_id, remarks)
    
    if success:
        return jsonify({"status": "success", "message": message}), 200
    else:
        return jsonify({"status": "error", "message": message}), 400

@request_bp.route("/api/admin/requests/<request_id>/reject", methods=["POST"])
@require_admin_auth
def reject_request(current_admin, request_id):
    """Admin rejects a request."""
    data = request.get_json() or {}
    remarks = data.get("remarks", "")
    
    success, message = RequestController.reject_request(str(current_admin["_id"]), request_id, remarks)
    
    if success:
        return jsonify({"status": "success", "message": message}), 200
    else:
        return jsonify({"status": "error", "message": message}), 400
