"""Contexte de requête propagé via contextvars (thread-safe, async-safe)."""
from contextvars import ContextVar

# Identifiant unique de corrélation, propagé de l'entrée HTTP jusqu'aux logs DB.
# Valeur par défaut vide pour les appels hors-requête (tâches de fond, tests).
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")
