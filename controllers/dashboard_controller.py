"""
Dashboard / Analytics Controller
Provides aggregate stats for the admin dashboard.
"""

import logging
from datetime import datetime, timezone, timedelta

from database.connection import get_db
from utils.response import success_response, error_response

logger = logging.getLogger(__name__)


class DashboardController:

    @staticmethod
    def get_overview(current_user: dict):
        """GET /api/dashboard/overview — Top-level KPIs."""
        db = get_db()
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)

        stats = {
            "users": {
                "total": db.users.count_documents({}),
                "active": db.users.count_documents({"is_active": True}),
                "new_last_30_days": db.users.count_documents({"created_at": {"$gte": thirty_days_ago}}),
            },
            "volunteers": {
                "total": db.volunteers.count_documents({}),
                "approved": db.volunteers.count_documents({"status": "approved"}),
                "pending": db.volunteers.count_documents({"status": "pending"}),
            },
            "events": {
                "total": db.events.count_documents({}),
                "published": db.events.count_documents({"status": "published"}),
                "upcoming": db.events.count_documents({
                    "date": {"$gte": now},
                }),
                "completed": db.events.count_documents({"date": {"$lt": now}}),
            },
            "registrations": {
                "total": db.join_requests.count_documents({}),
                "confirmed": db.join_requests.count_documents({"status": "approved"}),
                "pending": db.join_requests.count_documents({"status": "pending"}),
                "attended": db.join_requests.count_documents({"status": "attended"}),
            },
        }

        # Total volunteer hours
        pipeline = [{"$group": {"_id": None, "total_hours": {"$sum": "$hours_contributed"}}}]
        result = list(db.volunteers.aggregate(pipeline))
        stats["volunteers"]["total_hours"] = result[0]["total_hours"] if result else 0

        # Recent Users (last 5, volunteers only)
        recent_users_docs = list(db.users.find({"role": "volunteer"}).sort("created_at", -1).limit(5))
        recent_users = []
        for u in recent_users_docs:
            recent_users.append({
                "id": str(u["_id"]),
                "full_name": u.get("full_name", "Unknown"),
                "email": u.get("email", ""),
                "role": u.get("role", "volunteer"),
                "status": u.get("status", "active"),
                "created_at": u.get("created_at").isoformat() if u.get("created_at") else None
            })

        # Latest Activities (mocked using recent events and requests)
        recent_events = list(db.events.find().sort("created_at", -1).limit(2))
        recent_requests = list(db.join_requests.find().sort("applied_date", -1).limit(2))
        activities = []
        for e in recent_events:
            activities.append({
                "type": "event_created",
                "text": f"New event '{e.get('title')}' was created.",
                "time": e.get("created_at").isoformat() if e.get("created_at") else now.isoformat(),
                "icon": "bi-calendar-plus-fill text-primary"
            })
        for r in recent_requests:
            activities.append({
                "type": "request_received",
                "text": f"New join request received for event ID {str(r.get('event_id'))[:8]}",
                "time": r.get("applied_date").isoformat() if r.get("applied_date") else now.isoformat(),
                "icon": "bi-inbox-fill text-warning"
            })
        
        # Sort activities by time descending
        activities.sort(key=lambda x: x["time"], reverse=True)

        return success_response(data={
            "overview": stats,
            "recent_users": recent_users,
            "latest_activities": activities
        })

    @staticmethod
    def get_sidebar_stats(current_user: dict):
        """GET /api/dashboard/sidebar-stats — Fast counters for sidebar badges."""
        db = get_db()
        pending_requests = db.join_requests.count_documents({"status": "pending"})
        return success_response(data={
            "pending_requests": pending_requests
        })

    @staticmethod
    def get_event_trends(current_user: dict):
        """GET /api/dashboard/event-trends — Monthly event count for last 6 months."""
        from flask import request
        range_val = request.args.get("range", "6_months")
        db = get_db()
        now = datetime.now(timezone.utc)
        
        if range_val == "30_days":
            start_date = now - timedelta(days=30)
            group_by = {
                "year": {"$year": "$created_at"},
                "month": {"$month": "$created_at"},
                "day": {"$dayOfMonth": "$created_at"}
            }
        elif range_val == "this_year":
            start_date = datetime(now.year, 1, 1, tzinfo=timezone.utc)
            group_by = {
                "year": {"$year": "$created_at"},
                "month": {"$month": "$created_at"}
            }
        else:
            start_date = now - timedelta(days=180)
            group_by = {
                "year": {"$year": "$created_at"},
                "month": {"$month": "$created_at"}
            }

        pipeline = [
            {"$match": {"created_at": {"$gte": start_date}}},
            {"$group": {
                "_id": group_by,
                "count": {"$sum": 1},
            }},
            {"$sort": {"_id.year": 1, "_id.month": 1, "_id.day": 1} if range_val == "30_days" else {"_id.year": 1, "_id.month": 1}},
        ]
        trends = list(db.events.aggregate(pipeline))
        return success_response(data={"trends": trends, "range": range_val})

    @staticmethod
    def get_volunteer_by_skills(current_user: dict):
        """GET /api/dashboard/skills — Volunteer count grouped by skill."""
        db = get_db()
        pipeline = [
            {"$unwind": "$skills"},
            {"$group": {"_id": "$skills", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 20},
        ]
        skills = list(db.volunteers.aggregate(pipeline))
        return success_response(data={"skills": skills})

    @staticmethod
    def get_category_breakdown(current_user: dict):
        """GET /api/dashboard/categories — Event count grouped by category."""
        db = get_db()
        pipeline = [
            {"$group": {"_id": "$category", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ]
        categories = list(db.events.aggregate(pipeline))
        return success_response(data={"categories": categories})

    @staticmethod
    def get_volunteer_overview(current_user: dict):
        """GET /api/dashboard/volunteer — Volunteer personal dashboard data."""
        from bson import ObjectId
        db = get_db()
        user_id = ObjectId(current_user["_id"])
        now = datetime.now(timezone.utc)

        # Basic Stats
        total_hours = 0.0
        joined_events_count = 0
        pending_requests_count = 0
        
        # Aggregation for request counts and hours
        requests = list(db.join_requests.find({"user_id": user_id}))
        certificates_count = 0
        for req in requests:
            status = req.get("status")
            if status in ("approved", "attended"):
                joined_events_count += 1
            if status == "pending":
                pending_requests_count += 1
            if status == "attended":
                total_hours += float(req.get("hours_logged", 0.0))
                certificates_count += 1

        stats = {
            "joined_events": joined_events_count,
            "hours_logged": total_hours,
            "pending_requests": pending_requests_count,
            "certificates": certificates_count,
        }

        # Upcoming Events (approved & event start_date > now)
        pipeline_upcoming = [
            {"$match": {"user_id": user_id, "status": "approved"}},
            {"$lookup": {
                "from": "events",
                "localField": "event_id",
                "foreignField": "_id",
                "as": "event"
            }},
            {"$unwind": "$event"},
            {"$match": {"event.start_date": {"$gt": now}}},
            {"$sort": {"event.start_date": 1}},
            {"$limit": 4}
        ]
        upcoming_events = list(db.join_requests.aggregate(pipeline_upcoming))
        
        # Format upcoming events
        upcoming_formatted = []
        for doc in upcoming_events:
            ev = doc["event"]
            
            loc = ev.get("location", {})
            location_str = loc.get("venue", "") if isinstance(loc, dict) else str(loc)
            if isinstance(loc, dict) and loc.get("city"):
                location_str += f", {loc.get('city')}"
            location_str = location_str.strip(", ")

            upcoming_formatted.append({
                "id": str(ev["_id"]),
                "title": ev.get("title", ""),
                "location": location_str,
                "start_date": ev.get("date").isoformat() if ev.get("date") else None,
                "start_time": ev.get("start_time", "00:00"),
                "status": "Upcoming"
            })

        # Recent Pending Requests
        pipeline_pending = [
            {"$match": {"user_id": user_id, "status": "pending"}},
            {"$lookup": {
                "from": "events",
                "localField": "event_id",
                "foreignField": "_id",
                "as": "event"
            }},
            {"$unwind": "$event"},
            {"$sort": {"applied_date": -1}},
            {"$limit": 3}
        ]
        pending_docs = list(db.join_requests.aggregate(pipeline_pending))
        pending_formatted = []
        for doc in pending_docs:
            ev = doc["event"]
            pending_formatted.append({
                "id": str(ev["_id"]),
                "title": ev.get("title", ""),
                "applied_date": doc.get("applied_date").isoformat() if doc.get("applied_date") else None,
                "status": "Pending"
            })

        # History (attended/approved past events)
        pipeline_history = [
            {"$match": {"user_id": user_id, "status": {"$in": ["approved", "attended"]}}},
            {"$lookup": {
                "from": "events",
                "localField": "event_id",
                "foreignField": "_id",
                "as": "event"
            }},
            {"$unwind": "$event"},
            {"$match": {
                "$or": [
                    {"status": "attended"},
                    {"event.date": {"$lt": now}}
                ]
            }},
            {"$sort": {"event.date": -1}},
            {"$limit": 5}
        ]
        history_docs = list(db.join_requests.aggregate(pipeline_history))
        history_formatted = []
        for doc in history_docs:
            ev = doc["event"]
            
            loc = ev.get("location", {})
            location_str = loc.get("venue", "") if isinstance(loc, dict) else str(loc)
            if isinstance(loc, dict) and loc.get("city"):
                location_str += f", {loc.get('city')}"
            location_str = location_str.strip(", ")

            history_formatted.append({
                "id": str(ev["_id"]),
                "request_id": str(doc["_id"]),
                "title": ev.get("title", ""),
                "category": ev.get("category_name", "General"),
                "location": location_str,
                "start_date": ev.get("date").isoformat() if ev.get("date") else None,
                "hours_logged": doc.get("hours_logged", 0),
                "status": doc.get("status", "").capitalize(),
                "rating": doc.get("rating", None)
            })

        # Monthly Hours Trend (Last 6 Months)
        six_months_ago = now - timedelta(days=180)
        pipeline_trend = [
            {"$match": {
                "user_id": user_id, 
                "status": "attended",
                "updated_at": {"$gte": six_months_ago}
            }},
            {"$group": {
                "_id": {
                    "year": {"$year": "$updated_at"},
                    "month": {"$month": "$updated_at"},
                },
                "total_hours": {"$sum": "$hours_logged"}
            }},
            {"$sort": {"_id.year": 1, "_id.month": 1}}
        ]
        trend_docs = list(db.join_requests.aggregate(pipeline_trend))
        trend_formatted = [{"year": d["_id"]["year"], "month": d["_id"]["month"], "hours": d["total_hours"]} for d in trend_docs]

        # Categories Breakdown
        pipeline_cat = [
            {"$match": {"user_id": user_id, "status": {"$in": ["approved", "attended"]}}},
            {"$lookup": {
                "from": "events",
                "localField": "event_id",
                "foreignField": "_id",
                "as": "event"
            }},
            {"$unwind": "$event"},
            {"$group": {
                "_id": "$event.category",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}}
        ]
        cat_docs = list(db.join_requests.aggregate(pipeline_cat))
        cat_formatted = [{"category": d["_id"], "count": d["count"]} for d in cat_docs]
        
        # User details for profile card
        full_name = current_user.get("full_name", "")
        parts = full_name.split()
        first_name = parts[0] if parts else "Volunteer"
        last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
        
        user_info = {
            "first_name": first_name,
            "last_name": last_name,
            "created_at": current_user.get("created_at").isoformat() if current_user.get("created_at") else None,
            "completion_percentage": 75 # Mocked for now
        }

        # Recent Notifications
        from models.notification import NotificationModel
        recent_notifs, _ = NotificationModel.find_by_user(str(current_user["_id"]), page=1, page_size=4)
        unread_count = NotificationModel.count_unread(str(current_user["_id"]))
        notifs_formatted = [NotificationModel.serialize(n) for n in recent_notifs]

        return success_response(data={
            "stats": stats,
            "user_info": user_info,
            "upcoming_events": upcoming_formatted,
            "pending_requests": pending_formatted,
            "history": history_formatted,
            "hours_trend": trend_formatted,
            "categories": cat_formatted,
            "notifications": notifs_formatted,
            "unread_notifications_count": unread_count
        })
