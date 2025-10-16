"""Utility helper functions."""

import hashlib
from pathlib import Path
from typing import Any, Union
from datetime import datetime
import json


def generate_file_hash(content: bytes) -> str:
    """Generate SHA256 hash of file content."""
    return hashlib.sha256(content).hexdigest()


def ensure_dir_exists(path: Union[str, Path]) -> Path:
    """Ensure directory exists, create if not."""
    path_obj = Path(path)
    path_obj.mkdir(parents=True, exist_ok=True)
    return path_obj


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal attacks."""
    return Path(filename).name


def serialize_datetime(obj: Any) -> Any:
    """JSON serializer for datetime objects."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def safe_json_loads(data: str, default: Any = None) -> Any:
    """Safely load JSON, return default on error."""
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return default
