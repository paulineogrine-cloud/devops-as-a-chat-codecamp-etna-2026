import json
import logging
from datetime import datetime
from typing import Union

from sqlalchemy.orm import Session
from app import models

logger = logging.getLogger(__name__)


def _get_correlation_id() -> str:
    try:
        from app.core.context import correlation_id_var
        return correlation_id_var.get()
    except Exception:
        return ""


def log_execution_event(
    db: Session,
    execution_id: int,
    user_id: int,
    event: str,
    message: Union[str, dict],
    log_content: Union[str, dict] = "",
    level: str = "INFO",
):
    """Crée une entrée dans execution_logs.

    Convertit automatiquement les dicts en JSON.
    Attache le correlation_id courant pour relier le log à la requête HTTP d'origine.
    """
    if isinstance(message, dict):
        try:
            message = json.dumps(message, indent=2, ensure_ascii=False)
        except Exception as e:
            message = f"[ERREUR serialization JSON message] {e}"

    if isinstance(log_content, dict):
        try:
            log_content = json.dumps(log_content, indent=2, ensure_ascii=False)
        except Exception as e:
            log_content = f"[ERREUR serialization JSON log_content] {e}"

    cid = _get_correlation_id()
    logger.debug(
        "[execution_logger] save event=%s execution_id=%d correlation_id=%s",
        event, execution_id, cid or "-",
    )

    log = models.ExecutionLog(
        execution_id=execution_id,
        user_id=user_id,
        event=event,
        message=message,
        level=level,
        correlation_id=cid or None,
        created_at=datetime.utcnow(),
    )

    db.add(log)
    db.commit()
    logger.debug("[execution_logger] log enregistré execution_id=%d event=%s", execution_id, event)
