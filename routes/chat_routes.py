"""
Chat Routes & WebSockets — NGO Volunteer Management System
Handles real-time communication between volunteers within specific events.
"""

import os
import uuid
import logging
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, jsonify
from werkzeug.utils import secure_filename
from database.connection import get_db

logger = logging.getLogger(__name__)

# Standard Blueprint for the Chat Page
chat_bp = Blueprint("chat_bp", __name__)

# Ensure upload directory exists
UPLOAD_FOLDER = os.path.join("static", "uploads", "chat")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'webm'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@chat_bp.route("/chat", methods=["GET"])
def chat_page():
    """Render the global chat interface."""
    return render_template("chat.html", active_page="chat")

@chat_bp.route("/api/chat/upload", methods=["POST"])
def upload_media():
    """Handle multimedia uploads for the chat system."""
    # We should normally check JWT here, omitting for simplicity in MVP
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file"}), 400
        
    if file and allowed_file(file.filename):
        # Optional: restrict file size (e.g. max 10MB)
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        if size > 10 * 1024 * 1024:
            return jsonify({"status": "error", "message": "File too large. Max 10MB."}), 400
            
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = secure_filename(f"{uuid.uuid4().hex}.{ext}")
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        try:
            file.save(filepath)
            
            media_type = "video" if ext in ['mp4', 'webm'] else "image"
            media_url = f"/static/uploads/chat/{filename}"
            
            return jsonify({
                "status": "success",
                "data": {
                    "media_url": media_url,
                    "media_type": media_type
                }
            })
        except Exception as e:
            logger.error(f"Failed to save chat media: {e}")
            return jsonify({"status": "error", "message": "Failed to save file."}), 500
            
    return jsonify({"status": "error", "message": "Invalid file type. Allowed: png, jpg, jpeg, gif, mp4, webm"}), 400


# ── WebSockets Logic ────────────────────────────────────────────────────────
def register_socket_events(socketio):
    """
    Registers SocketIO event handlers.
    Called from app.py to avoid circular imports.
    """
    
    @socketio.on("connect")
    def handle_connect():
        logger.info(f"🟢 Client Connected to Chat: {request.sid}")

    @socketio.on("disconnect")
    def handle_disconnect():
        logger.info(f"🔴 Client Disconnected: {request.sid}")

    @socketio.on("join")
    def handle_join(data=None):
        if data is None: data = {}
        from flask_socketio import join_room
        username = data.get("username", "Anonymous")
        event_id = data.get("event_id")
        
        if not event_id:
            return
            
        join_room(event_id)
        logger.info(f"👤 {username} joined event chat: {event_id}")
        
        # Broadcast that the user joined only to this room
        socketio.emit("user_joined", {"username": username, "time": datetime.now(timezone.utc).isoformat()}, to=event_id)

    @socketio.on("send_message")
    def handle_send_message(data=None):
        if data is None: data = {}
        username = data.get("username", "Anonymous")
        text = data.get("message", "")
        event_id = data.get("event_id")
        media_url = data.get("media_url")
        media_type = data.get("media_type")
        
        # Must have either text or media
        if not event_id or (not text and not media_url):
            return
            
        message_doc = {
            "event_id": event_id,
            "username": username,
            "message": text,
            "timestamp": datetime.now(timezone.utc)
        }
        
        if media_url:
            message_doc["media_url"] = media_url
            message_doc["media_type"] = media_type
        
        # Save to DB
        try:
            get_db().chats.insert_one(message_doc)
        except Exception as e:
            logger.error(f"Failed to save chat message: {e}")
            
        # Convert datetime to string for JSON serialization
        message_doc["timestamp"] = message_doc["timestamp"].isoformat()
        message_doc["_id"] = str(message_doc.get("_id", ""))
        
        # Broadcast only to the specific event room
        socketio.emit("receive_message", message_doc, to=event_id)

    @socketio.on("get_history")
    def handle_get_history(data=None):
        """Send the last 50 messages to the newly connected client for a specific event."""
        if data is None: data = {}
        event_id = data.get("event_id")
        if not event_id:
            return
            
        try:
            # Fetch last 50 messages for this specific event sorted by timestamp ascending
            cursor = get_db().chats.find({"event_id": event_id}).sort("timestamp", -1).limit(50)
            messages = list(cursor)
            messages.reverse()  # Oldest first for the UI
            
            # Format for client
            formatted = []
            for msg in messages:
                formatted.append({
                    "username": msg.get("username", "Unknown"),
                    "message": msg.get("message", ""),
                    "media_url": msg.get("media_url"),
                    "media_type": msg.get("media_type"),
                    "timestamp": msg.get("timestamp").isoformat() if isinstance(msg.get("timestamp"), datetime) else msg.get("timestamp", "")
                })
                
            socketio.emit("chat_history", {"messages": formatted}, to=request.sid)
        except Exception as e:
            logger.error(f"Failed to fetch chat history: {e}")
