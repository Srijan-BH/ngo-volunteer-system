"""
Request Logger Middleware
Logs all incoming requests and their response times.
"""

import time
import logging
from flask import Flask, request, g

logger = logging.getLogger(__name__)


def register_request_logger(app: Flask):
    """Register before/after request hooks for logging."""

    @app.before_request
    def start_timer():
        g.start_time = time.perf_counter()

    @app.after_request
    def log_request(response):
        duration_ms = (time.perf_counter() - getattr(g, "start_time", time.perf_counter())) * 1000
        logger.info(
            f"{request.method} {request.path} "
            f"[{response.status_code}] "
            f"{duration_ms:.2f}ms "
            f"IP={request.remote_addr}"
        )
        # Append CORS-friendly headers
        response.headers["X-Request-ID"] = request.headers.get("X-Request-ID", "")
        return response
