# app/services/log_analyzer_service.py
from app.services.gpt_service import analyze_execution_logs


def _detect_engine(logs: list[str]) -> str:
    joined = "\n".join(logs[:20]).lower()
    if "ansible" in joined or "play recap" in joined or "task [" in joined:
        return "ansible"
    return "terraform"


async def analyze_logs(logs: list[str], engine: str | None = None) -> dict:
    """Analyse les logs et retourne un résumé IA structuré."""
    detected = engine or _detect_engine(logs)
    result = await analyze_execution_logs(logs, detected)
    return {
        "status": result.get("status", "warning"),
        "summary": result.get("summary", "Analyse non disponible."),
        "fix": result.get("fix", None),
    }
