# © 2024–2026 TOURE Arnaud Patrick
# Licensed under the MIT License

"""
Structured Error Response - Erreurs actionnables et debuggables
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class ErrorResponse:
    """Erreur structurée, claire et actionnelle"""
    error_code: str      # ACTION_NOT_FOUND, ANSIBLE_FAILED, etc.
    error_message: str   # Message clair pour l'utilisateur
    details: Optional[Dict[str, Any]] = None   # Détails techniques optionnels
    user_action: Optional[str] = None          # Ce que l'utilisateur peut faire
    correlation_id: Optional[str] = None       # ID de corrélation (traçabilité logs)

    def to_dict(self):
        d: Dict[str, Any] = {
            "error_code": self.error_code,
            "error_message": self.error_message,
            "details": self.details or {},
            "user_action": self.user_action,
        }
        if self.correlation_id:
            d["correlation_id"] = self.correlation_id
        return d


# Codes d'erreur standardisés
ERROR_CODES = {
    "ACTION_NOT_FOUND": "L'action n'a pas été reconnue.",
    "ACTION_AMBIGUOUS": "Plusieurs actions correspondent. Précise laquelle.",
    "NO_TARGETS": "Aucune cible (instance) sélectionnée.",
    "NO_INSTANCES_AVAILABLE": "Aucune instance AWS disponible.",
    "SSM_UNAVAILABLE": "SSM n'est pas disponible sur les instances.",
    "SSM_FAILED": "Échec de la communication SSM avec les instances.",
    "ANSIBLE_FAILED": "L'exécution Ansible a échoué.",
    "CREDENTIALS_MISSING": "Les credentials AWS manquent.",
    "SYNTAX_ERROR": "La commande n'a pas la bonne syntaxe.",
    "UNKNOWN_ERROR": "Une erreur inattendue s'est produite.",
}


def make_error(
    error_code: str,
    user_action: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None,
) -> ErrorResponse:
    """Factory pour créer une ErrorResponse avec le bon message."""
    if correlation_id is None:
        try:
            from app.core.context import correlation_id_var
            correlation_id = correlation_id_var.get() or None
        except Exception:
            pass
    message = ERROR_CODES.get(error_code, ERROR_CODES["UNKNOWN_ERROR"])
    return ErrorResponse(
        error_code=error_code,
        error_message=message,
        details=details,
        user_action=user_action,
        correlation_id=correlation_id,
    )
