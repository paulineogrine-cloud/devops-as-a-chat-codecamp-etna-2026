# © 2024–2026 TOURE Arnaud Patrick
# Licensed under the MIT License

"""
Intent Detection - Nouvelle structure unifiée
Retourne des détails complets, pas seulement le type d'intent.
"""

from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any

# All supported intent types (Challenge 2 — extended taxonomy)
SUPPORTED_INTENTS = {
    # Core DevOps actions (routed to execution pipeline)
    "create":          "Créer/provisionner une infrastructure cloud",
    "configure":       "Configurer ou installer un service sur une machine",
    "audit":           "Auditer la sécurité d'une machine",
    "monitoring":      "Surveiller les métriques d'une machine",
    # New intents — handled via free_chat / generative flow
    "check_status":    "Consulter le statut d'un service ou d'une ressource",
    "explain_error":   "Expliquer ou analyser une erreur / un log",
    "generate_config": "Générer un fichier de configuration",
    "help":            "Demander de l'aide sur DAC ou DevOps",
    # Fallback intents
    "free_chat":       "Conversation libre hors contexte DevOps structuré",
    "unknown":         "Intention non reconnue — clarification nécessaire",
}


@dataclass
class DetectedIntent:
    """Résultat unifié de détection d'intent"""
    intent_type: str  # One of SUPPORTED_INTENTS keys

    action_id: Optional[str] = None  # Pour configure: "install_nginx", etc.
    action_candidates: Optional[List[Dict[str, Any]]] = None  # Si ambigu

    confidence: float = 0.0  # 0.0–1.0
    recognized_keywords: List[str] = None  # Keywords détectés

    params: Optional[Dict[str, Any]] = None  # Paramètres extraits (provider, os, …)
    missing_params: Optional[List[str]] = None  # Paramètres manquants critiques
    suggestions: Optional[List[str]] = None  # Suggestions pour intents inconnus
    debug: Optional[Dict[str, Any]] = None  # Info debug

    def __post_init__(self):
        if self.recognized_keywords is None:
            self.recognized_keywords = []
        if self.params is None:
            self.params = {}
        if self.missing_params is None:
            self.missing_params = []

    def to_dict(self):
        return asdict(self)

    def is_ambiguous(self) -> bool:
        """True si plusieurs candidates possibles"""
        return bool(self.action_candidates and len(self.action_candidates) > 1)

    def is_complete(self) -> bool:
        """True si intent complet et prêt à exécuter"""
        if self.intent_type == "configure":
            return bool(self.action_id)
        if self.intent_type in ["create", "audit", "monitoring"]:
            return True
        return True

    def is_unknown(self) -> bool:
        return self.intent_type == "unknown"
