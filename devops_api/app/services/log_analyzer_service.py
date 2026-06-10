# © 2024–2026 TOURE Arnaud Patrick
# Licensed under the MIT License

# app/services/log_analyzer_service.py
"""
Service d'analyse intelligente des logs Terraform / Ansible.
Utilise GPT via gpt_service.analyze_execution_logs pour produire un résumé
humain en français, utile aux développeurs débutants.
"""

import logging
from app.services.gpt_service import analyze_execution_logs

logger = logging.getLogger(__name__)

# Mots-clés qui permettent de deviner le moteur si non fourni
_TERRAFORM_HINTS = {"terraform", "plan", "apply", "destroy", "provider", "resource", "module"}
_ANSIBLE_HINTS   = {"ansible", "playbook", "task", "play", "ok:", "changed:", "fatal:", "skipping:"}


def _detect_engine(logs: list[str]) -> str:
    """Tente de deviner l'outil (terraform/ansible) à partir des logs."""
    sample = "\n".join(logs[:30]).lower()
    tf_score  = sum(1 for kw in _TERRAFORM_HINTS if kw in sample)
    ans_score = sum(1 for kw in _ANSIBLE_HINTS  if kw in sample)
    if tf_score >= ans_score:
        return "terraform"
    return "ansible"


async def analyze_logs(logs: list[str], engine: str | None = None) -> dict:
    """
    Point d'entrée principal du service.

    Args:
        logs:   Lignes de logs bruts (liste de str).
        engine: 'terraform' | 'ansible' | None (auto-détection).

    Returns:
        dict {
            status:  'success' | 'error' | 'warning',
            summary: str,
            fix:     str | None
        }
    """
    if not logs:
        return {
            "status": "warning",
            "summary": "Aucun log disponible pour cette exécution.",
            "fix": None,
        }

    detected = engine or _detect_engine(logs)
    logger.info(f"[log_analyzer] Analyse {len(logs)} lignes (engine={detected})")

    result = await analyze_execution_logs(logs, detected)

    # Garantir la structure attendue même si l'IA retourne quelque chose d'inattendu
    return {
        "status":  result.get("status",  "warning"),
        "summary": result.get("summary", "Analyse indisponible."),
        "fix":     result.get("fix",     None),
    }
