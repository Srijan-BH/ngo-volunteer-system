"""
Routes Package — NGO Volunteer Management System
Registers all Blueprint routes with the Flask application.
"""

from flask import Flask


def register_blueprints(app: Flask):
    """Import and register all route blueprints."""

    # ── Auth ──────────────────────────────────────────────────────────────────
    from routes.auth_routes       import auth_bp
    from routes.admin_auth_routes import admin_auth_bp

    # ── Resources ─────────────────────────────────────────────────────────────
    from routes.user_routes         import user_bp
    from routes.volunteer_routes    import volunteer_bp
    from routes.event_routes        import event_bp
    from routes.notification_routes import notification_bp
    from routes.dashboard_routes    import dashboard_bp
    from routes.request_routes      import request_bp
    from routes.chat_routes         import chat_bp

    app.register_blueprint(auth_bp,         url_prefix="/api/auth")
    app.register_blueprint(admin_auth_bp,   url_prefix="/api/admin/auth")
    app.register_blueprint(user_bp,         url_prefix="/api/users")
    app.register_blueprint(volunteer_bp,    url_prefix="/api/volunteers")
    app.register_blueprint(event_bp,        url_prefix="/api/events")
    app.register_blueprint(notification_bp, url_prefix="/api/notifications")
    app.register_blueprint(dashboard_bp,    url_prefix="/api/dashboard")
    app.register_blueprint(chat_bp)
    app.register_blueprint(request_bp)

    app.logger.info("All blueprints registered successfully.")
