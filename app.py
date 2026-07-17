"""
NGO Volunteer Management System
Main Application Entry Point
"""

import eventlet
eventlet.monkey_patch()

import logging
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO
from flask_talisman import Talisman

from config.settings import Config, get_config
from database.connection import init_db
from routes import register_blueprints
from middleware.error_handlers import register_error_handlers
from utils.logger import setup_logger

# Initialize global extensions
limiter = Limiter(key_func=get_remote_address)
socketio = SocketIO(cors_allowed_origins="*")

def create_app(config_class=None):
    """Application factory function."""
    app = Flask(__name__)

    # Load configuration
    if config_class is None:
        config_class = get_config()
    app.config.from_object(config_class)

    # Setup logger
    setup_logger(app)

    # Initialize CORS
    CORS(app, resources={r"/api/*": {"origins": app.config.get("CORS_ORIGINS", "*")}})

    # Initialize Rate Limiting
    limiter.init_app(app)

    # Initialize SocketIO
    socketio.init_app(app)
    from routes.chat_routes import register_socket_events
    register_socket_events(socketio)

    # Initialize Secure Headers (Talisman)
    # Note: content_security_policy is set to None for this prototype to avoid breaking inline scripts/styles,
    # but in a strict production app, a robust CSP should be configured.
    is_secure = app.config.get("SESSION_COOKIE_SECURE", False)
    Talisman(
        app,
        content_security_policy=None,
        force_https=is_secure,
        strict_transport_security=is_secure,
        session_cookie_secure=is_secure,
        session_cookie_http_only=True
    )

    # Initialize database
    init_db(app)

    # Register all blueprints
    register_blueprints(app)

    # Register error handlers
    register_error_handlers(app)

    # ── Global Request Sanitization ───────────────────────────────────────────
    from utils.security import sanitize_mongo_input
    
    @app.before_request
    def sanitize_request():
        """Sanitize all incoming JSON payloads to prevent database injection."""
        if request.is_json and request.json:
            sanitized = sanitize_mongo_input(request.json)
            try:
                request._cached_json = (sanitized, sanitized) # (data, original text representation essentially)
            except Exception:
                pass # If it fails due to Werkzeug version, controllers should manually sanitize.

    # ── Public Page Routes ────────────────────────────────────────────────
    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/about")
    def about():
        return render_template("about.html")

    @app.route("/contact")
    def contact():
        return render_template("contact.html")

    @app.route("/faq")
    def faq():
        return render_template("faq.html")

    @app.route("/privacy")
    def privacy():
        return render_template("privacy.html")

    @app.route("/terms")
    def terms():
        return render_template("terms.html")

    # ── Auth Page Routes ──────────────────────────────────────────────────
    @app.route("/login")
    def login_page():
        return render_template("auth/login.html")

    @app.route("/register")
    def register_page():
        return render_template("auth/signup.html")

    @app.route("/forgot-password")
    def forgot_password_page():
        return render_template("auth/forgot_password.html")

    # ── App Page Routes ───────────────────────────────────────────────────
    @app.route("/dashboard")
    def dashboard():
        return render_template("dashboard.html", active_page="dashboard")

    @app.route("/events")
    def events_page():
        return render_template("events.html", active_page="events")

    @app.route("/my-events")
    def my_events_page():
        return render_template("my_events.html", active_page="my-events")

    @app.route("/my-requests")
    def my_requests_page():
        return render_template("my_requests.html", active_page="my-requests")

    @app.route("/profile")
    def profile_page():
        return render_template("profile.html", active_page="profile")

    @app.route("/notifications")
    def notifications_page():
        return render_template("notifications.html", active_page="notifications")

    @app.route("/settings")
    def settings_page():
        return render_template("settings.html", active_page="settings")

    @app.route("/certificate/<request_id>")
    def certificate_page(request_id):
        return render_template("certificate.html", request_id=request_id)

    @app.route("/admin/login")
    def admin_login_page():
        return render_template("admin/login.html", active_page="admin_login")

    @app.route("/admin/dashboard")
    def admin_dashboard():
        return render_template("admin/dashboard.html", active_page="admin_dashboard")

    @app.route("/admin/events")
    def admin_events():
        return render_template("admin/events.html", active_page="admin_events")

    @app.route("/admin/events/new")
    def admin_event_create():
        return render_template("admin/events/form.html", active_page="admin_events")

    @app.route("/admin/volunteers")
    def admin_volunteers():
        return render_template("admin/volunteers.html", active_page="admin_users")

    @app.route("/admin/requests")
    def admin_requests():
        return render_template("admin/requests.html", active_page="admin_requests")

    @app.route("/theme-test")
    def theme_test():
        return render_template("theme_test.html", active_page="dashboard")

    @app.route("/api/contact", methods=["POST"])
    def submit_contact_form():
        from utils.email_service import EmailService
        
        data = request.json or {}
        name = data.get("name")
        email = data.get("email")
        phone = data.get("phone", "N/A")
        subject = data.get("subject", "General Inquiry")
        message = data.get("message")
        
        if not name or not email or not message:
            return jsonify({"status": "error", "message": "Missing required fields"}), 422
            
        # Build HTML Email
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #0d6efd; border-bottom: 2px solid #0d6efd; padding-bottom: 10px;">New Contact Form Submission</h2>
            <p><strong>Name:</strong> {name}</p>
            <p><strong>Email:</strong> {email}</p>
            <p><strong>Phone:</strong> {phone}</p>
            <p><strong>Subject:</strong> {subject}</p>
            <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #6c757d; margin-top: 20px;">
                <h4 style="margin-top: 0; margin-bottom: 10px;">Message:</h4>
                <p style="white-space: pre-wrap; margin: 0;">{message}</p>
            </div>
        </body>
        </html>
        """
        
        # Send to the specified admin email
        success = EmailService.send_email("ngo.admin.alerts@gmail.com", f"Contact Form: {subject}", html_body)
        
        if success:
            return jsonify({"status": "success", "message": "Message sent successfully"}), 200
        else:
            return jsonify({"status": "error", "message": "Failed to send message. Try again later."}), 500

    # ── API Health Check ──────────────────────────────────────────────────
    @app.route("/health", methods=["GET"])
    def health_check():
        return jsonify({"status": "healthy", "service": "ngo-volunteer-system"}), 200

    app.logger.info("NGO Volunteer Management System started successfully.")
    return app


if __name__ == "__main__":
    app = create_app()
    socketio.run(
        app,
        host=app.config.get("HOST", "127.0.0.2"),
        port=int(app.config.get("PORT", 5000)),
        debug=app.config.get("DEBUG", False)
    )
