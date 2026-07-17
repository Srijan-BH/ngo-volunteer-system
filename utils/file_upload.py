"""
File Upload Utilities
Handles secure file uploads for profile pictures and event images.
"""

import os
import uuid
import logging
from typing import Optional
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from flask import current_app

logger = logging.getLogger(__name__)

# Upload type to folder mapping
UPLOAD_TYPES = {
    "profile": "PROFILE_UPLOAD_FOLDER",
    "event": "EVENT_UPLOAD_FOLDER",
}


def allowed_file(filename: str, upload_type: str = "profile") -> bool:
    """Check if the file extension is allowed."""
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    if upload_type == "event":
        allowed = current_app.config.get("ALLOWED_IMAGE_EXTENSIONS", set()) | \
                  current_app.config.get("ALLOWED_DOC_EXTENSIONS", set())
    else:
        allowed = current_app.config.get("ALLOWED_IMAGE_EXTENSIONS", {"png", "jpg", "jpeg", "gif", "webp"})
    return ext in allowed


def save_upload(
    file: FileStorage,
    upload_type: str = "profile",
    custom_filename: Optional[str] = None,
) -> dict:
    """
    Save an uploaded file securely.
    Returns dict: {"success": bool, "filename": str, "url": str, "error": str}
    """
    if not file or not file.filename:
        return {"success": False, "error": "No file selected.", "filename": "", "url": ""}

    if not allowed_file(file.filename, upload_type):
        return {"success": False, "error": "File type not allowed.", "filename": "", "url": ""}
        
    # Strict MIME type validation
    allowed_mimes = current_app.config.get("ALLOWED_IMAGE_EXTENSIONS", set())
    mimetype = file.mimetype.lower()
    if not any(mimetype.endswith(ext) for ext in allowed_mimes) and 'image' not in mimetype:
        if upload_type != "event" or 'application' not in mimetype:
            return {"success": False, "error": "Invalid file content type.", "filename": "", "url": ""}

    # Check file size explicitly (Max 16MB)
    MAX_SIZE = current_app.config.get("MAX_CONTENT_LENGTH", 16 * 1024 * 1024)
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > MAX_SIZE:
        return {"success": False, "error": "File exceeds maximum allowed size.", "filename": "", "url": ""}

    folder_key = UPLOAD_TYPES.get(upload_type, "PROFILE_UPLOAD_FOLDER")
    upload_folder = current_app.config.get(folder_key, "uploads/profiles")

    # Ensure directory exists
    os.makedirs(upload_folder, exist_ok=True)

    ext = file.filename.rsplit(".", 1)[1].lower()
    # Enforce safe filenames without directory traversal risks
    filename = secure_filename(custom_filename or f"{uuid.uuid4().hex}.{ext}")

    filepath = os.path.join(upload_folder, filename)

    try:
        file.save(filepath)
        url = f"/uploads/{upload_type}s/{filename}"
        logger.info(f"File saved: {filepath} (Size: {size} bytes)")
        return {"success": True, "filename": filename, "url": url, "error": ""}
    except Exception as exc:
        logger.exception(f"File save error: {exc}")
        return {"success": False, "error": "Failed to save file.", "filename": "", "url": ""}


def delete_upload(filename: str, upload_type: str = "profile") -> bool:
    """Delete a previously uploaded file."""
    folder_key = UPLOAD_TYPES.get(upload_type, "PROFILE_UPLOAD_FOLDER")
    upload_folder = current_app.config.get(folder_key, "uploads/profiles")
    filepath = os.path.join(upload_folder, secure_filename(filename))

    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            logger.info(f"File deleted: {filepath}")
            return True
        except Exception as exc:
            logger.warning(f"Could not delete file {filepath}: {exc}")
    return False


def get_file_size_mb(file: FileStorage) -> float:
    """Return the file size in MB."""
    file.seek(0, 2)  # Seek to end
    size_bytes = file.tell()
    file.seek(0)  # Reset
    return size_bytes / (1024 * 1024)
