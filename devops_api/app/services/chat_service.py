# © 2024–2026 TOURE Arnaud Patrick
# Licensed under the MIT License

import logging
import re

from app.paths import LOGS_DIR
logger = logging.getLogger(__name__)

import os
import json
import logging
from app.services.gpt_service import generate_free_chat_completion

#  Répertoire des logs
BASE_LOG_DIR = LOGS_DIR
os.makedirs(BASE_LOG_DIR, exist_ok=True)
LOG_FILE_PATH = os.path.join(BASE_LOG_DIR, "chat_service.log")

#  Création du logger
logger = logging.getLogger("chat_service")
logger.setLevel(logging.INFO)

#  Évite les handlers en double
if not logger.hasHandlers():
    handler = logging.FileHandler(LOG_FILE_PATH)
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

#  Safe JSON loader for GPT responses
def safe_json_loads(text: str) -> dict:
    """
    Safely parse JSON from GPT responses.
    Handles markdown formatting, json prefix, and other common issues.
    """
    try:
        cleaned = text.strip()
        # Remove markdown code blocks
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        # Remove "json" prefix if present
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
        # Extract JSON object {...}
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("no_json_object_found")
        return json.loads(cleaned[start:end+1])
    except Exception as e:
        logger.error(f"Failed to parse JSON: {e}, text was: {text[:200]}")
        raise ValueError(f"JSON parsing failed: {e}")

# Challenge 2 — unified intent detection engine (replaces Ubuntu/service fast-tracks + GPT flow)
from app.services.intent_engine import detect_intent


async def detect_intent_and_action(request_text: str) -> dict:
    """
    Analyse le prompt utilisateur pour détecter l'intention DevOps et extraire les paramètres.

    Délègue au moteur hybride (intent_engine) qui applique deux couches :
      1. Règles / regex (sans IA, déterministe)
      2. Validation catalogue pour les actions 'configure'

    Retourne un dict backward-compatible avec chat_creation_routes.
    """
    logger.info("detect_intent_and_action: '%s'", request_text)

    result = detect_intent(request_text)

    logger.info(
        "Intent détecté: intent=%s action=%s confidence=%.2f params=%s",
        result.intent, result.action, result.confidence, result.params,
    )

    return result.to_legacy_dict()

#  Réponse libre avec GPT
async def generate_free_chat_response(request_text: str = None, user_message: str = None, context: str = None) -> str:
    """
    Utilise GPT pour répondre librement à une question ou un échange conversationnel.
    Paramètres compatibles: request_text (legacy) ou user_message + context (nouveau)
    """
    # Support des deux signatures pour rétrocompatibilité
    question = user_message or request_text or "Question vide"
    
    # Construction du prompt avec contexte optionnel
    prompt_parts = [
        "Tu es un assistant DevOps expérimenté et sympathique.",
        "IMPORTANT : Réponds TOUJOURS en français, peu importe la langue de la question.",
        "Réponds clairement et de façon concise à la question suivante.",
        "Si la question concerne DevOps, donne une réponse technique.",
        "Si la question est générale, réponds poliment.\n"
    ]
    
    if context:
        prompt_parts.append(f"Contexte de la session : {context}\n")
    
    prompt_parts.append(f"Question utilisateur : {question}\n\nRéponse (en français) :")
    
    prompt = "\n".join(prompt_parts)

    response = await generate_free_chat_completion(prompt)
    response_limited = response.strip()[:1500]

    logger.info("Free chat request: %s", question)
    logger.info("Free chat response: %s", response_limited)

    return response_limited

#  Extraction de paramètres basée sur des mots-clés (fallback)
def extract_params_from_text(request_text: str) -> dict:
    """
    Extraction manuelle de paramètres à partir du texte utilisateur (fallback).
    """
    text = request_text.lower()
    params = {}
    
    # Provider detection
    if any(kw in text for kw in ["aws", "amazon"]):
        params["provider"] = "aws"
    elif any(kw in text for kw in ["azure", "microsoft"]):
        params["provider"] = "azure"
    elif any(kw in text for kw in ["gcp", "google"]):
        params["provider"] = "gcp"
    
    # OS detection
    if "ubuntu" in text:
        params["os"] = "ubuntu"
    elif "centos" in text:
        params["os"] = "centos"
    elif "debian" in text:
        params["os"] = "debian"
    elif "windows" in text:
        params["os"] = "windows"
    
    # Instance type detection
    import re
    instance_match = re.search(r't[0-9]+\.[a-z]+', text)
    if instance_match:
        params["instance_type"] = instance_match.group()
    
    # Region detection
    region_match = re.search(r'(eu|us|ap)-[a-z]+-[0-9]+', text)
    if region_match:
        params["region"] = region_match.group()
    
    # Services detection
    services = []
    service_keywords = ["nginx", "apache", "docker", "mysql", "postgresql", "redis", "mongodb"]
    for service in service_keywords:
        if service in text:
            services.append(service)
    if services:
        params["services"] = services
    
    # Audit tool detection
    if "lynis" in text:
        params["audit_tool"] = "lynis"
    elif "auditd" in text:
        params["audit_tool"] = "auditd"
    
    return params

#  Détection rapide fallback par mots-clés
def detect_intent_type(request_text: str) -> str:
    """
    Détection rapide et manuelle d’intention basée sur des mots-clés.
    """
    text = request_text.lower()

    if any(kw in text for kw in [
        "créer", "creer", "création", "déployer", "deploie", "lancer", "déploie",
        "vm", "instance", "serveur", "machine", "ubuntu", "aws", "vps",
        "nouvelle", "nouveau"  # Ajout pour couvrir plus de cas
    ]):
        return "create"

    elif any(kw in text for kw in [
        "configurer", "installer", "setup", "mettre à jour", "activer",
        "nginx", "mysql", "apache", "docker", "ufw", "ssh", "firewall"
    ]):
        return "configure"

    elif any(kw in text for kw in [
        "auditer", "vérifier", "scanner", "audit", "sécurité", "securite", 
        "hardening", "vulnérabilités", "vulnerabilites", "scan de sécurité"
    ]):
        return "audit"

    elif any(kw in text for kw in [
        "monitoring", "métriques", "metriques", "dashboard", "surveiller",
        "cpu", "mémoire", "memoire", "disque", "performances", "stats",
        "charge", "load", "uptime", "monitoring"
    ]):
        return "monitoring"

    elif any(kw in text for kw in [
        "kubernetes", "k8s", "pod", "cluster", "deployment", "namespace", "helm"
    ]):
        return "kubernetes"

    else:
        return "unknown"
