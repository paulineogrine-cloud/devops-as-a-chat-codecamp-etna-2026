from __future__ import annotations

import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime, timezone
from typing import Any, Optional

class JSONFormatter(logging.Formatter):
    """Émet chaque log en une seule ligne JSON parseable."""

    def format(self, record: logging.LogRecord) -> str:
        try:
            from app.core.context import correlation_id_var
            cid = correlation_id_var.get("")
        except Exception:
            cid = ""

        obj: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if cid:
            obj["correlation_id"] = cid
        if record.exc_info:
            obj["exc"] = self.formatException(record.exc_info)
        return json.dumps(obj, ensure_ascii=False)


def setup_logging(level: Optional[str] = None) -> None:
    """Configure le logger root avec JSONFormatter une seule fois au démarrage."""
    if level is None:
        level = os.getenv("DAC_LOG_LEVEL") or os.getenv("LOG_LEVEL") or "info"
    numeric = getattr(logging, level.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(numeric)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


SENSITIVE_KEYS = {
    "access_key_id",
    "aws_access_key_id",
    "secret_access_key",
    "aws_secret_access_key",
    "session_token",
    "token",
    "password",
    "private_key",
    "authorization",
}

REDACTED = "***REDACTED***"


def _is_sensitive_key(key: str) -> bool:
    return key.strip().lower() in SENSITIVE_KEYS


def ensure_timezone_aware(dt: datetime | None) -> datetime | None:
    """
    Convert naive datetime to timezone-aware (UTC).
    
    This ensures ISO8601 serialization includes timezone info like +00:00 or Z.
    PostgreSQL DateTime(timezone=True) stores UTC but may return naive datetime objects.
    
    Args:
        dt: A datetime object (may be naive or aware)
    
    Returns:
        A timezone-aware datetime in UTC, or None if input is None
    """
    if dt is None:
        return None
    
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            # Naive datetime - assume UTC
            return dt.replace(tzinfo=timezone.utc)
        else:
            # Already aware
            return dt
    
    return dt


def redact_secrets(obj: Any) -> Any:
    """Recursively redact sensitive fields from dicts/lists/objects."""
    if obj is None:
        return obj

    if isinstance(obj, dict):
        redacted: dict[str, Any] = {}
        for k, v in obj.items():
            if _is_sensitive_key(str(k)):
                redacted[k] = REDACTED
            else:
                redacted[k] = redact_secrets(v)
        return redacted

    if isinstance(obj, (list, tuple, set)):
        return [redact_secrets(v) for v in obj]

    if hasattr(obj, "model_dump") and callable(getattr(obj, "model_dump")):
        return redact_secrets(obj.model_dump())

    if hasattr(obj, "dict") and callable(getattr(obj, "dict")):
        return redact_secrets(obj.dict())

    return obj
