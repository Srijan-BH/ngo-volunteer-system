"""
Logger Setup
Configures application-wide logging with file and console handlers.
"""

import logging
import logging.handlers
import os
from flask import Flask


def setup_logger(app: Flask) -> None:
    """Configure logging for the Flask application."""
    log_level_str = app.config.get("LOG_LEVEL", "INFO")
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    log_file = app.config.get("LOG_FILE", "logs/app.log")

    # Ensure log directory exists
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    # Log format
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ─── Console Handler ─────────────────────────────────────────────────────
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    # ─── Rotating File Handler ────────────────────────────────────────────────
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    # ─── Root Logger ─────────────────────────────────────────────────────────
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # ─── Flask App Logger ─────────────────────────────────────────────────────
    app.logger.setLevel(log_level)
    if not app.logger.handlers:
        app.logger.addHandler(console_handler)
        app.logger.addHandler(file_handler)

    # Silence noisy third-party loggers
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.INFO)  # Keep INFO so the startup URL is printed

    app.logger.info(f"Logger initialized. Level: {log_level_str}, File: {log_file}")
