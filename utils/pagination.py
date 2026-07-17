"""
Pagination Utilities
Extract and validate pagination parameters from request query string.
"""

from flask import Request
from flask import current_app


def get_pagination_params(request: Request) -> tuple[int, int]:
    """
    Extract `page` and `page_size` from request query params.
    Applies defaults and enforces max page_size from config.
    Returns (page, page_size).
    """
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (ValueError, TypeError):
        page = 1

    try:
        default_size = current_app.config.get("DEFAULT_PAGE_SIZE", 10)
        max_size = current_app.config.get("MAX_PAGE_SIZE", 100)
        page_size = int(request.args.get("page_size", default_size))
        page_size = max(1, min(page_size, max_size))
    except (ValueError, TypeError):
        page_size = 10

    return page, page_size
