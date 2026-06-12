# © 2026 ETNA CodeCamp — Challenge 2: Intent Detection
# Licensed under the MIT License

"""
Intent Detection Engine — hybrid rule/regex approach.

Architecture (2 layers, no AI dependency):
  Layer 1 — Rules:   keyword scoring + regex patterns → confidence 0.6-0.95
  Layer 2 — Catalog: for 'configure' intents, validates against config_catalog

Public API:
  engine = IntentEngine()
  result: IntentResult = engine.detect("je veux installer nginx sur mon serveur")
  result.intent          # "configure"
  result.action          # "configure_service"
  result.confidence      # 0.85
  result.params          # {"services": ["nginx"]}
  result.action_id       # "install_nginx"
"""

import re
import unicodedata
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple

from app.services.config_catalog import match_config_action

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Intent Taxonomy
# ─────────────────────────────────────────────────────────────────────────────

INTENT_DEFINITIONS: Dict[str, str] = {
    "create":          "Créer/provisionner une infrastructure cloud (VM, réseau, etc.)",
    "configure":       "Configurer ou installer un service sur une machine existante",
    "audit":           "Auditer la sécurité d'une machine ou d'une infrastructure",
    "monitoring":      "Surveiller les métriques ou l'état d'une machine",
    "check_status":    "Consulter le statut d'un service ou d'une ressource",
    "explain_error":   "Expliquer ou analyser une erreur / un message de log",
    "generate_config": "Générer un fichier de configuration (Terraform, Nginx, Ansible…)",
    "help":            "Demander de l'aide sur DAC ou une commande DevOps",
    "free_chat":       "Conversation libre hors contexte DevOps structuré",
    "unknown":         "Intention non reconnue — clarification nécessaire",
}

# Intent → DevOps action identifier used by the routing layer
INTENT_TO_ACTION: Dict[str, str] = {
    "create":          "create",
    "configure":       "configure",
    "audit":           "audit",
    "monitoring":      "monitoring",
    "check_status":    "free_chat",
    "explain_error":   "free_chat",
    "generate_config": "free_chat",
    "help":            "free_chat",
    "free_chat":       "free_chat",
    "unknown":         "none",
}

# ─────────────────────────────────────────────────────────────────────────────
# Detection Rules
# Each intent has:
#   keywords       — simple lowercase substrings (score +1.0 each)
#   patterns       — regex applied to normalised text (score +1.5 each, higher precision)
#   base_confidence — ceiling applied after normalisation
# ─────────────────────────────────────────────────────────────────────────────

_RULES: Dict[str, Dict] = {
    "create": {
        "keywords": [
            # Verbs of creation — specific enough to imply infrastructure
            "créer", "creer", "crée",
            "creation", "création",
            "provisionner", "provision",
            "déployer", "deployer", "déploie", "deploie",
            "nouvelle instance", "nouvel instance",
            # English
            "create", "deploy",
            "new instance", "new vm",
            # Infrastructure nouns that strongly imply creation in context
            "instance", "vm",
        ],
        "patterns": [
            r"\b(?:une?|des?)\s+(?:nouvelle?|nouveau)\s+(?:instance|vm|machine|serveur)\b",
            r"\b(?:instance|vm|machine|serveur)\s+(?:ubuntu|centos|debian|windows)\b",
            r"\b(?:ubuntu|centos|debian)\s+(?:instance|vm|machine|serveur)\b",
        ],
        "base_confidence": 0.85,
    },
    "configure": {
        "keywords": [
            "configurer", "configure",
            # All conjugated install forms in French
            "installer", "install", "installe", "installez", "installons",
            "setup", "set up",
            "mettre en place",
            "activer",
            "paramétrer", "parametrer",
            "mettre à jour", "mettre a jour",
        ],
        "patterns": [
            # Catches any conjugated form of install* before a service name
            r"\binstall\w*\s+(?:nginx|apache|docker|mysql|redis|postgresql|git|node|fail2ban|ufw)\b",
            r"\b(?:configurer?|configure|setup)\s+(?:nginx|apache|ufw|ssh|firewall|ssl|tls|docker)\b",
        ],
        "base_confidence": 0.80,
    },
    "audit": {
        "keywords": [
            "audit", "auditer",
            "vérifier", "verifier",
            "scanner", "scan",
            "sécurité", "securite", "security",
            "hardening", "durcir",
            "vulnérabilité", "vulnerabilite", "vulnerability",
        ],
        "patterns": [
            r"\baudit\s+(?:de\s+)?s[ée]curit[ée]\b",
            r"\bscan\s+(?:de\s+)?s[ée]curit[ée]\b",
            # Specific security tools = strong signal (1.5 pts) over generic "lance" (1.0 pt)
            r"\b(?:lynis|auditd|fail2ban|clamav)\b",
        ],
        "base_confidence": 0.85,
    },
    "monitoring": {
        "keywords": [
            "monitoring", "monitorer",
            "surveiller", "observer",
            "métriques", "metriques", "metrics",
            "grafana", "prometheus",
            "cpu", "ram", "mémoire", "memoire", "disque", "disk",
            "performances", "performance",
            "uptime", "charge", "load",
        ],
        "patterns": [
            r"\b(?:surveiller|monitorer)\s+(?:les\s+)?(?:m[ée]triques|performances|ressources)\b",
            # "grafana/prometheus + install/config" as a pattern (stronger signal for monitoring)
            r"\b(?:grafana|prometheus)\b.*\b(?:install|config|setup|surveiller|monitorer)\b",
        ],
        "base_confidence": 0.85,
    },
    "check_status": {
        "keywords": [
            "statut", "status",
            "état", "etat",
            "tourne", "marche", "fonctionne",
            "actif",
            "ping",
            "voir les instances", "lister les instances",
            "afficher les ressources",
        ],
        "patterns": [
            r"\best[- ]ce\s+que\s+\w+\s+(?:tourne|fonctionne|actif)\b",
            r"\bstatut\s+(?:du\s+)?(?:service|instance|serveur)\b",
            r"\b(?:voir|afficher|lister)\s+(?:les\s+)?(?:instances|services|ressources)\b",
        ],
        "base_confidence": 0.75,
    },
    "explain_error": {
        "keywords": [
            "erreur", "error",
            "exception",
            "problème", "probleme", "problem",
            "bug", "crash",
            "failed", "failure",
            "traceback", "stack trace",
            "pourquoi ca plante",
            "expliquer erreur", "analyser erreur",
        ],
        "patterns": [
            r"error\s*:\s*\S+",
            r"exception\s*:\s*\S+",
            r"\b(?:exit code|errno)\s+\d+\b",
            r"\b(?:connection refused|permission denied|no such file|command not found)\b",
            r"\bpourquoi\s+(?:ca|[cç]a)\s+(?:plante|marche pas|fonctionne pas)\b",
        ],
        "base_confidence": 0.80,
    },
    "generate_config": {
        "keywords": [
            # All conjugated forms (after accent normalisation)
            "generer", "genere", "generez",
            "cree un fichier", "creer un fichier",
            "template",
            "playbook",
            "nginx.conf", "dockerfile",
            "fichier de config",
        ],
        "patterns": [
            # Conjugated verb + config noun
            r"\bgener\w+\s+(?:une?\s+)?(?:config(?:uration)?|fichier|template|playbook)\b",
            r"\b(?:creer?|cree)\s+(?:une?\s+)?(?:config(?:uration)?|fichier|template)\b",
            r"\b(?:terraform|ansible|dockerfile|kubernetes)\s+(?:config|template|fichier|exemple)\b",
            r"\bmontre[- ]moi\s+(?:une?\s+)?(?:config(?:uration)?|exemple|template)\b",
        ],
        "base_confidence": 0.80,
    },
    "help": {
        "keywords": [
            "aide", "help",
            "comment faire",
            "c'est quoi", "c est quoi",
            "tutorial", "tutoriel",
            "documentation", "doc",
            "comment utiliser dac",
        ],
        "patterns": [
            r"\bcomment\s+(?:faire|utiliser|configurer|installer)\b",
            r"\bqu'?est[- ]ce\s+que\b",
            r"\b(?:aide|help)\s*\??\s*$",
            r"\b(?:tutoriel|tutorial)\b",
        ],
        "base_confidence": 0.70,
    },
}

# Priority order when two intents score equally (more specific first)
_PRIORITY = [
    "explain_error",
    "generate_config",
    "create",
    "configure",
    "audit",
    "monitoring",
    "check_status",
    "help",
    "free_chat",
    "unknown",
]

# ─────────────────────────────────────────────────────────────────────────────
# Parameter extraction
# ─────────────────────────────────────────────────────────────────────────────

_PROVIDER_PATTERNS: Dict[str, List[str]] = {
    "aws":   [r"\baws\b", r"\bamazon\b"],
    "azure": [r"\bazure\b", r"\bmicrosoft\b"],
    "gcp":   [r"\bgcp\b", r"\bgoogle\s*cloud\b"],
}

_OS_PATTERNS: Dict[str, List[str]] = {
    "ubuntu":  [r"\bubuntu\b"],
    "centos":  [r"\bcentos\b"],
    "debian":  [r"\bdebian\b"],
    "windows": [r"\bwindows\b"],
}

_INSTANCE_TYPE_RE = re.compile(r"\bt[23][a-z]?\.[a-z0-9]+\b")
_REGION_RE        = re.compile(r"\b(?:eu|us|ap|ca|sa)-[a-z]+-[0-9]+\b")
_PORT_RE          = re.compile(r"\bport\s+([0-9]{2,5})\b")

_KNOWN_SERVICES   = ["nginx", "apache", "docker", "mysql", "postgresql", "redis",
                     "mongodb", "fail2ban", "ufw", "ssh", "git", "node", "nodejs",
                     "prometheus", "grafana"]

_CONFIG_TYPES     = ["terraform", "ansible", "nginx", "dockerfile", "kubernetes", "k8s"]


# ─────────────────────────────────────────────────────────────────────────────
# Result dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class IntentResult:
    intent: str
    action: str
    confidence: float
    description: str
    params: Dict[str, Any]             = field(default_factory=dict)
    missing_params: List[str]          = field(default_factory=list)
    action_id: Optional[str]           = None   # e.g. "install_nginx" for configure
    matched_keywords: List[str]        = field(default_factory=list)
    suggestions: Optional[List[str]]   = None   # shown for unknown intents

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent":           self.intent,
            "action":           self.action,
            "confidence":       self.confidence,
            "description":      self.description,
            "params":           self.params,
            "missing_params":   self.missing_params,
            "action_id":        self.action_id,
            "matched_keywords": self.matched_keywords,
            "suggestions":      self.suggestions,
        }

    def to_legacy_dict(self) -> Dict[str, Any]:
        """Backward-compatible format expected by chat_creation_routes."""
        return {
            "action":           self.action,
            "description":      self.description,
            "extracted_params": self.params,
            "missing_params":   self.missing_params,
            "confidence_score": self.confidence,
            # richer fields for new consumers
            "intent":           self.intent,
            "action_id":        self.action_id,
            "matched_keywords": self.matched_keywords,
            "suggestions":      self.suggestions,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Engine
# ─────────────────────────────────────────────────────────────────────────────

class IntentEngine:
    """
    Stateless intent detection engine.
    Thread-safe; a single instance can be shared across requests.
    """

    # Minimum confidence to accept a rule-based match
    CONFIDENCE_THRESHOLD = 0.40

    def detect(self, text: str) -> IntentResult:
        """
        Detect the intent of *text*.

        Returns an IntentResult with all extracted information.
        Falls back to 'unknown' with suggestions when nothing matches.
        """
        if not text or not text.strip():
            return self._unknown_result("Texte vide fourni.", [])

        normalised = _normalise(text)
        scores = self._score_all(normalised)

        if not scores:
            return self._unknown_result(text, [])

        # Pick the best-scoring intent, respecting priority for ties
        best_intent, best_score, matched_kw = self._pick_best(scores)

        if best_score < self.CONFIDENCE_THRESHOLD:
            return self._unknown_result(text, list(scores.keys()))

        confidence = min(best_score, 1.0)
        params = _extract_params(normalised)
        action = INTENT_TO_ACTION[best_intent]

        # Layer 2: catalog validation for configure
        action_id = None
        if best_intent == "configure":
            action_id, catalog_kw, catalog_conf, _ = match_config_action(text)
            matched_kw = list(set(matched_kw + catalog_kw))
            if catalog_conf > 0:
                confidence = min(confidence + 0.05, 1.0)

        description = self._describe(best_intent, params, action_id, text)
        missing = self._missing_params(best_intent, params)

        return IntentResult(
            intent=best_intent,
            action=action,
            confidence=round(confidence, 2),
            description=description,
            params=params,
            missing_params=missing,
            action_id=action_id,
            matched_keywords=matched_kw,
        )

    # ── private helpers ──────────────────────────────────────────────────────

    def _score_all(self, normalised: str) -> Dict[str, Tuple[float, List[str]]]:
        """Score every intent against the normalised text."""
        results: Dict[str, Tuple[float, List[str]]] = {}

        for intent, rules in _RULES.items():
            score = 0.0
            matched: List[str] = []

            # Keyword hits — deduplicate after normalisation to avoid inflated scores
            # when multiple list entries reduce to the same normalised form (e.g. "créer"/"creer")
            seen_kw_norms: set = set()
            for kw in rules["keywords"]:
                kw_norm = _normalise(kw)
                if kw_norm in seen_kw_norms:
                    continue
                seen_kw_norms.add(kw_norm)
                if kw_norm in normalised:
                    score += 1.0
                    matched.append(kw)

            # Regex hits (higher weight — more specific)
            for pattern in rules["patterns"]:
                if re.search(pattern, normalised, re.IGNORECASE):
                    score += 1.5
                    matched.append(f"pattern:{pattern[:30]}")

            if score > 0:
                # Non-linear scale: 1 match → ~0.57, 2 matches → ~0.69, 3 → ~0.81
                # Ensures any match clears the 0.40 threshold.
                raw_confidence = min(0.45 + score * 0.12, rules["base_confidence"])
                results[intent] = (raw_confidence, matched)

        return results

    def _pick_best(
        self,
        scores: Dict[str, Tuple[float, List[str]]],
    ) -> Tuple[str, float, List[str]]:
        """Return (intent, confidence, matched_keywords) for the winner."""
        # Sort by confidence desc, then by priority
        ranked = sorted(
            scores.items(),
            key=lambda x: (-x[1][0], _PRIORITY.index(x[0]) if x[0] in _PRIORITY else 99),
        )
        best_intent, (best_conf, best_kw) = ranked[0]
        return best_intent, best_conf, best_kw

    @staticmethod
    def _describe(intent: str, params: Dict, action_id: Optional[str], raw: str) -> str:
        """Build a human-readable description of the detected intent."""
        descriptions = {
            "create":          "Créer une infrastructure cloud",
            "configure":       f"Configurer {action_id or 'un service'} sur une machine",
            "audit":           "Réaliser un audit de sécurité",
            "monitoring":      "Surveiller les métriques d'une machine",
            "check_status":    "Consulter le statut d'un service ou d'une ressource",
            "explain_error":   "Expliquer une erreur ou un message de log",
            "generate_config": "Générer un fichier de configuration",
            "help":            "Aide sur DAC ou une commande DevOps",
            "free_chat":       "Conversation libre",
        }

        base = descriptions.get(intent, INTENT_DEFINITIONS.get(intent, "Intention détectée"))

        if intent == "create":
            details = []
            if params.get("provider"):
                details.append(f"sur {params['provider'].upper()}")
            if params.get("os"):
                details.append(f"avec {params['os']}")
            if params.get("instance_type"):
                details.append(f"({params['instance_type']})")
            if details:
                base += " " + " ".join(details)

        if intent == "configure" and params.get("services"):
            base = f"Configurer {', '.join(params['services'])} sur une machine"

        return base

    @staticmethod
    def _missing_params(intent: str, params: Dict) -> List[str]:
        """List critical params that were not extracted."""
        missing = []
        if intent == "create":
            if not params.get("provider"):
                missing.append("provider (aws/azure/gcp)")
            if not params.get("os"):
                missing.append("os (ubuntu/centos/debian)")
        return missing

    @staticmethod
    def _unknown_result(raw_text: str, candidate_intents: List[str]) -> IntentResult:
        suggestions = [
            INTENT_DEFINITIONS[i]
            for i in candidate_intents[:3]
            if i in INTENT_DEFINITIONS
        ] or [
            "Créer une instance cloud — ex: «crée une VM Ubuntu sur AWS»",
            "Configurer un service — ex: «installe nginx»",
            "Auditer la sécurité — ex: «lance un audit de sécurité»",
            "Expliquer une erreur — ex: «pourquoi j'ai connection refused ?»",
        ]
        return IntentResult(
            intent="unknown",
            action="none",
            confidence=0.0,
            description="Je n'ai pas compris votre demande. Voici quelques exemples:",
            suggestions=suggestions,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Text normalisation helper
# ─────────────────────────────────────────────────────────────────────────────

def _normalise(text: str) -> str:
    """Lowercase, strip accents, collapse whitespace."""
    text = text.lower()
    text = "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ─────────────────────────────────────────────────────────────────────────────
# Parameter extraction
# ─────────────────────────────────────────────────────────────────────────────

def _extract_params(normalised: str) -> Dict[str, Any]:
    """Extract structured params from a normalised message."""
    params: Dict[str, Any] = {}

    # Provider
    for provider, patterns in _PROVIDER_PATTERNS.items():
        if any(re.search(p, normalised) for p in patterns):
            params["provider"] = provider
            break

    # OS
    for os_name, patterns in _OS_PATTERNS.items():
        if any(re.search(p, normalised) for p in patterns):
            params["os"] = os_name
            break

    # Instance type (e.g. t2.micro, t3.small)
    m = _INSTANCE_TYPE_RE.search(normalised)
    if m:
        params["instance_type"] = m.group()

    # AWS region (e.g. eu-west-1)
    m = _REGION_RE.search(normalised)
    if m:
        params["region"] = m.group()

    # TCP port
    m = _PORT_RE.search(normalised)
    if m:
        params["port"] = int(m.group(1))

    # Services mentioned
    found_services = [s for s in _KNOWN_SERVICES if s in normalised]
    if found_services:
        params["services"] = found_services

    # Config file type
    found_config = [c for c in _CONFIG_TYPES if c in normalised]
    if found_config:
        params["config_type"] = found_config

    return params


# ─────────────────────────────────────────────────────────────────────────────
# Module-level singleton
# ─────────────────────────────────────────────────────────────────────────────

_engine = IntentEngine()


def detect_intent(text: str) -> IntentResult:
    """Convenience function wrapping the shared engine instance."""
    return _engine.detect(text)
