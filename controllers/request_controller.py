"""
Volunteer Request Controller
Handles the business logic for event join requests.
"""

from typing import Tuple, Dict, Any
import logging
import threading

from models.join_request import JoinRequestModel, STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED, STATUS_WITHDRAWN
from models.event import EventModel, STATUS_PUBLISHED
from models.user import UserModel
from models.notification import NotificationModel
from utils.email_service import EmailService

logger = logging.getLogger(__name__)

class RequestController:

    # ─── USER ACTIONS ────────────────────────────────────────────────────────

    @staticmethod
    def apply_for_event(user_id: str, event_id: str, user_remarks: str = "") -> Tuple[bool, str, Dict[str, Any]]:
        """
        User applies for an event.
        - Validates event exists and is published
        - Checks capacity
        - Prevents duplicate requests
        - Creates JoinRequest (pending)
        - Generates notification
        """
        # 1. Check Event
        event = EventModel.find_by_id(event_id)
        if not event:
            return False, "Event not found.", {}

        if event.get("status") != STATUS_PUBLISHED:
            return False, "This event is not open for registration.", {}

        # 2. Check Capacity
        capacity_info = EventModel.check_capacity(event_id)
        if capacity_info.get("is_full"):
            return False, "This event has reached its maximum capacity.", {}

        # 3. Check Duplicates
        existing = JoinRequestModel.find_by_user_and_event(user_id, event_id)
        if existing:
            if existing.get("status") in [STATUS_PENDING, STATUS_APPROVED]:
                return False, "You have already applied for this event.", {}
            elif existing.get("status") == STATUS_REJECTED:
                return False, "Your previous application for this event was rejected.", {}
            elif existing.get("status") == STATUS_WITHDRAWN:
                JoinRequestModel.delete(str(existing["_id"]))

        # 4. Create Request
        # We delete withdrawn requests above, so this will safely create a new one.
        request_id = JoinRequestModel.create(user_id, event_id, user_remarks)

        # 5. Notify User
        NotificationModel.notify_join_request(
            user_id=user_id,
            event_title=event.get("title", "Event"),
            event_id=event_id
        )

        return True, "Request submitted successfully.", {"request_id": request_id}

    @staticmethod
    def withdraw_request(user_id: str, request_id: str) -> Tuple[bool, str]:
        """
        User cancels their own request.
        If it was already approved, we need to free up a spot in the event.
        """
        req = JoinRequestModel.find_by_id(request_id)
        if not req:
            return False, "Request not found."
            
        if str(req.get("user_id")) != user_id:
            return False, "Unauthorized."

        current_status = req.get("status")
        if current_status not in [STATUS_PENDING, STATUS_APPROVED]:
            return False, f"Cannot withdraw a request with status '{current_status}'."

        success = JoinRequestModel.withdraw(request_id)
        if success and current_status == STATUS_APPROVED:
            # Free up a spot
            EventModel.increment_participants(str(req.get("event_id")), delta=-1)
            
        return success, "Request withdrawn successfully."

    @staticmethod
    def get_user_requests(user_id: str, status: str = None, page: int = 1, page_size: int = 10) -> Tuple[list, int]:
        """Get paginated requests for a specific user, with event details populated."""
        requests, total = JoinRequestModel.find_by_user(user_id, status=status, page=page, page_size=page_size)
        
        # Populate event details
        populated = []
        for req in requests:
            event = EventModel.find_by_id(str(req.get("event_id")))
            req_data = JoinRequestModel.serialize(req)
            req_data["event"] = EventModel.serialize(event) if event else None
            populated.append(req_data)
            
        return populated, total

    @staticmethod
    def get_certificate_data(user_id: str, request_id: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Get data required to generate a certificate for an attended request.
        """
        req = JoinRequestModel.find_by_id(request_id)
        if not req:
            return False, "Request not found.", {}
            
        if str(req.get("user_id")) != user_id:
            return False, "Unauthorized.", {}
            
        if req.get("status") != "attended":
            return False, "Certificate is only available for attended events.", {}
            
        event = EventModel.find_by_id(str(req.get("event_id")))
        if not event:
            return False, "Event not found.", {}
            
        user = UserModel.find_by_id(user_id)
        if not user:
            return False, "User not found.", {}
            
        data = {
            "volunteer_name": user.get("full_name", "Volunteer"),
            "event_title": event.get("title", "Event"),
            "date": event.get("start_date").strftime("%B %d, %Y") if event.get("start_date") else (req.get("updated_at").strftime("%B %d, %Y") if req.get("updated_at") else "Unknown Date"),
            "hours": req.get("hours_logged", 0)
        }
        
        return True, "Success", data

    @staticmethod
    def submit_feedback(user_id: str, request_id: str, rating: int, feedback: str) -> Tuple[bool, str]:
        """
        User submits feedback and rating for an event they attended.
        """
        req = JoinRequestModel.find_by_id(request_id)
        if not req:
            return False, "Request not found."
            
        if str(req.get("user_id")) != user_id:
            return False, "Unauthorized."
            
        if req.get("status") != "attended":
            return False, "Feedback can only be submitted for attended events."
            
        if req.get("rating") is not None:
            return False, "Feedback has already been submitted for this event."
            
        success = JoinRequestModel.add_feedback(request_id, rating, feedback)
        if success:
            return True, "Feedback submitted successfully."
        return False, "Failed to submit feedback."

    # ─── ADMIN ACTIONS ───────────────────────────────────────────────────────

    @staticmethod
    def get_all_requests(status: str = None, page: int = 1, page_size: int = 10) -> Tuple[list, int]:
        """Get paginated requests for admins, optionally filtered by status."""
        filters = {"status": status} if status else {}
        requests, total = JoinRequestModel.find_all(filters=filters, page=page, page_size=page_size)
        populated = []
        for req in requests:
            event = EventModel.find_by_id(str(req.get("event_id")))
            user = UserModel.find_by_id(str(req.get("user_id")))
            req_data = JoinRequestModel.serialize(req)
            req_data["event"] = EventModel.serialize(event) if event else None
            req_data["user"] = {
                "name": user.get("full_name", "Unknown"),
                "email": user.get("email", ""),
            } if user else None
            populated.append(req_data)
        return populated, total

    @staticmethod
    def get_pending_requests(page: int = 1, page_size: int = 10) -> Tuple[list, int]:
        """Get paginated pending requests for admins."""
        return RequestController.get_all_requests(STATUS_PENDING, page, page_size)

    @staticmethod
    def get_event_requests(event_id: str, status: str = None, page: int = 1, page_size: int = 10) -> Tuple[list, int]:
        requests, total = JoinRequestModel.find_by_event(event_id, status, page, page_size)
        populated = []
        for req in requests:
            user = UserModel.find_by_id(str(req.get("user_id")))
            req_data = JoinRequestModel.serialize(req)
            req_data["user"] = {
                "name": user.get("full_name", "Unknown"),
                "email": user.get("email", ""),
            } if user else None
            populated.append(req_data)
        return populated, total

    @staticmethod
    def approve_request(admin_id: str, request_id: str, remarks: str = "") -> Tuple[bool, str]:
        """
        Admin approves a request.
        - Checks capacity again to be safe
        - Updates status to approved
        - Increments event participants
        - Notifies user
        """
        req = JoinRequestModel.find_by_id(request_id)
        if not req:
            return False, "Request not found."

        if req.get("status") != STATUS_PENDING:
            return False, f"Request is not pending (current status: {req.get('status')})."

        event_id = str(req.get("event_id"))
        event = EventModel.find_by_id(event_id)
        
        # Check capacity just in case it filled up while pending
        if event:
            cap = EventModel.check_capacity(event_id)
            if cap.get("is_full"):
                return False, "Cannot approve: Event has reached maximum capacity."

        success = JoinRequestModel.approve(request_id, admin_id, remarks)
        if success:
            EventModel.increment_participants(event_id, delta=1)
            NotificationModel.notify_approval(
                user_id=str(req.get("user_id")),
                event_title=event.get("title", "Event") if event else "Event",
                event_id=event_id
            )
            
            # Send Email
            user = UserModel.find_by_id(str(req.get("user_id")))
            if user and user.get("email"):
                event_date_str = event.get("date").strftime("%B %d, %Y") if event and event.get("date") else "Upcoming"
                threading.Thread(
                    target=EmailService.send_approval_email,
                    kwargs={
                        "to_email": user.get("email"),
                        "volunteer_name": user.get("full_name", "Volunteer"),
                        "event_title": event.get("title", "Event") if event else "Event",
                        "event_date": event_date_str
                    }
                ).start()
                
            return True, "Request approved successfully."
            
        return False, "Failed to approve request."

    @staticmethod
    def reject_request(admin_id: str, request_id: str, remarks: str) -> Tuple[bool, str]:
        """
        Admin rejects a request.
        - Updates status to rejected
        - Notifies user
        """
        req = JoinRequestModel.find_by_id(request_id)
        if not req:
            return False, "Request not found."

        if req.get("status") != STATUS_PENDING:
            return False, f"Request is not pending (current status: {req.get('status')})."

        if not remarks or len(remarks.strip()) < 3:
            return False, "Remarks are required for rejection."

        success = JoinRequestModel.reject(request_id, admin_id, remarks)
        if success:
            event = EventModel.find_by_id(str(req.get("event_id")))
            NotificationModel.notify_rejection(
                user_id=str(req.get("user_id")),
                event_title=event.get("title", "Event") if event else "Event",
                event_id=str(req.get("event_id")),
                reason=remarks
            )
            return True, "Request rejected."
            
        return False, "Failed to reject request."

    @staticmethod
    def mark_request_attended(admin_id: str, request_id: str, hours: float) -> Tuple[bool, str]:
        """
        Admin marks an approved request as attended and logs hours.
        """
        req = JoinRequestModel.find_by_id(request_id)
        if not req:
            return False, "Request not found."

        if req.get("status") != STATUS_APPROVED:
            return False, f"Request must be approved first (current status: {req.get('status')})."

        success = JoinRequestModel.mark_attended(request_id, hours)
        if success:
            event = EventModel.find_by_id(str(req.get("event_id")))
            event_title = event.get("title", "Event") if event else "Event"
            
            # Increment volunteer total hours
            from models.volunteer import VolunteerModel
            volunteer = VolunteerModel.find_by_user_id(str(req.get("user_id")))
            if volunteer:
                VolunteerModel.add_hours(str(volunteer["_id"]), hours)
                
            NotificationModel.notify_certificate_available(
                user_id=str(req.get("user_id")),
                event_title=event_title,
                request_id=request_id
            )
            
            # Send Email
            user = UserModel.find_by_id(str(req.get("user_id")))
            if user and user.get("email"):
                threading.Thread(
                    target=EmailService.send_award_email,
                    kwargs={
                        "to_email": user.get("email"),
                        "volunteer_name": user.get("full_name", "Volunteer"),
                        "event_title": event_title,
                        "hours": hours
                    }
                ).start()
                
            return True, "Volunteer marked as attended and hours awarded."
        
        return False, "Failed to update attendance."
