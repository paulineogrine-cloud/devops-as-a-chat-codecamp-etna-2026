from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any

# ─── Structured JSON logger ───────────────────────────────────────────────────

class JSONFormatter(logging.Formatter):
    """Formatteur qui émet chaque log comme une ligne JSON.

    Le correlation_id est lu depuis le ContextVar s'il est disponible,
    sinon depuis l'attribut extra du record (pour les tests unitaires).
    """

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        # Lire le correlation_id depuis le ContextVar (requête HTTP en cours)
        cid: str = ""
        try:
            from app.core.context import correlation_id_var
            cid = correlation_id_var.get()
        except Exception:
            pass
        # Fallback : attribut extra passé explicitement au logger
        if not cid:
            cid = getattr(record, "correlation_id", "")
        if cid:
            entry["correlation_id"] = cid
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False)


_logging_configured = False


def setup_logging(level: str = "INFO", log_file: str | None = None) -> None:
    """Configure le logger root une seule fois (idempotent).

    Tous les modules qui font ``logging.getLogger(__name__)`` héritent
    automatiquement de cette configuration sans créer leurs propres handlers.
    """
    global _logging_configured
    if _logging_configured:
        return

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    fmt = JSONFormatter()

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    root.addHandler(console)

    if log_file:
        try:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            fh = logging.FileHandler(log_file, encoding="utf-8")
            fh.setFormatter(fmt)
            root.addHandler(fh)
        except Exception as e:
            root.warning("Impossible d'ouvrir le fichier de log %s : %s", log_file, e)

    _logging_configured = True


def get_logger(name: str) -> logging.Logger:
    """Raccourci : retourne un logger enfant du root configuré."""
    return logging.getLogger(name)


# ─── Utilitaires existants ────────────────────────────────────────────────────

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
