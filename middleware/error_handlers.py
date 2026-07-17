"""
Error Handlers Middleware
Registers global HTTP error handlers on the Flask application.
"""

import logging
from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


def register_error_handlers(app: Flask):
    """Register all application-wide error handlers."""

    @app.errorhandler(400)
    def bad_request(error):
        logger.warning(f"400 Bad Request: {error}")
        return jsonify({
            "status": "error",
            "code": 400,
            "message": "Bad request. Please check your input.",
            "error": str(error),
        }), 400

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({
            "status": "error",
            "code": 401,
            "message": "Unauthorized. Authentication is required.",
        }), 401

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            "status": "error",
            "code": 403,
            "message": "Forbidden. You do not have permission to access this resource.",
        }), 403

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "status": "error",
            "code": 404,
            "message": "The requested resource was not found.",
        }), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({
            "status": "error",
            "code": 405,
            "message": "HTTP method not allowed for this endpoint.",
        }), 405

    @app.errorhandler(409)
    def conflict(error):
        return jsonify({
            "status": "error",
            "code": 409,
            "message": "Conflict. The resource already exists.",
        }), 409

    @app.errorhandler(413)
    def request_entity_too_large(error):
        return jsonify({
            "status": "error",
            "code": 413,
            "message": "File too large. Maximum upload size exceeded.",
        }), 413

    @app.errorhandler(422)
    def unprocessable_entity(error):
        return jsonify({
            "status": "error",
            "code": 422,
            "message": "Unprocessable entity. Validation failed.",
        }), 422

    @app.errorhandler(429)
    def too_many_requests(error):
        return jsonify({
            "status": "error",
            "code": 429,
            "message": "Too many requests. Please slow down.",
        }), 429

    @app.errorhandler(500)
    def internal_server_error(error):
        logger.exception(f"500 Internal Server Error: {error}")
        return jsonify({
            "status": "error",
            "code": 500,
            "message": "An internal server error occurred. Please try again later.",
        }), 500

    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        logger.warning(f"HTTP Exception {error.code}: {error}")
        return jsonify({
            "status": "error",
            "code": error.code,
            "message": error.description,
        }), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        logger.exception(f"Unexpected error: {error}")
        return jsonify({
            "status": "error",
            "code": 500,
            "message": "An unexpected error occurred.",
        }), 500
