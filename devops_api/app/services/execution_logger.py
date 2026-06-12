import logging
logger = logging.getLogger(__name__)

import json
from sqlalchemy.orm import Session
from app import models
from datetime import datetime
from typing import Union, Optional


def log_execution_event(
    db: Session,
    execution_id: int,
    user_id: int,
    event: str,
    message: Union[str, dict],
    log_content: Union[str, dict] = "",
    level: str = "INFO",
    correlation_id: Optional[str] = None,
):
    """
    Crée une entrée dans execution_logs.
    Convertit automatiquement les dicts en JSON pour éviter les erreurs SQL.
    """
    if isinstance(message, dict):
        try:
            message = json.dumps(message, indent=2, ensure_ascii=False)
        except Exception as e:
            message = f"[ERREUR de serialization JSON message] {str(e)}"

    if isinstance(log_content, dict):
        try:
            log_content = json.dumps(log_content, indent=2, ensure_ascii=False)
        except Exception as e:
            log_content = f"[ERREUR de serialization JSON log_content] {str(e)}"

    if correlation_id is None:
        try:
            from app.core.context import correlation_id_var
            correlation_id = correlation_id_var.get("") or None
        except Exception:
            correlation_id = None

    logger.debug("[LOGGER] Log : execution_id=%s event=%s level=%s", execution_id, event, level)

    log = models.ExecutionLog(
        execution_id=execution_id,
        user_id=user_id,
        event=event,
        message=message,
        level=level.upper(),
        correlation_id=correlation_id,
        created_at=datetime.utcnow()
    )

    db.add(log)
    db.commit()
    logger.debug("[LOGGER] Log enregistré.")
