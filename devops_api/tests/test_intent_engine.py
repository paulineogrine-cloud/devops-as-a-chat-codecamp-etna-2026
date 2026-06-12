# © 2026 ETNA CodeCamp — Challenge 2: Intent Detection Tests

"""
Unit tests for the intent_engine module.

Run with:
    cd devops_api
    pytest tests/test_intent_engine.py -v

No AI key, no network, no database required — pure deterministic tests.
"""

import sys
import os

# Allow running from the devops_api directory without installing the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.services.intent_engine import IntentEngine, detect_intent, INTENT_TO_ACTION

engine = IntentEngine()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def assert_intent(text: str, expected_intent: str, min_confidence: float = 0.4):
    result = engine.detect(text)
    assert result.intent == expected_intent, (
        f"[{text!r}] Expected intent={expected_intent!r}, got {result.intent!r} "
        f"(confidence={result.confidence:.2f}, keywords={result.matched_keywords})"
    )
    assert result.confidence >= min_confidence, (
        f"[{text!r}] Confidence too low: {result.confidence:.2f} < {min_confidence}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Intent: create
# ─────────────────────────────────────────────────────────────────────────────

class TestCreateIntent:
    def test_simple_create_fr(self):
        assert_intent("je veux créer une instance ubuntu", "create")

    def test_create_with_provider(self):
        assert_intent("crée une VM Ubuntu sur AWS en eu-west-1", "create")

    def test_deploy_verb(self):
        assert_intent("déploie un serveur debian", "create")

    def test_provision_verb(self):
        assert_intent("provisionner une nouvelle machine", "create")

    def test_create_english(self):
        assert_intent("create an ubuntu instance on aws", "create")

    def test_create_with_instance_type(self):
        result = engine.detect("lance une instance t2.micro ubuntu")
        assert result.intent == "create"
        assert result.params.get("instance_type") == "t2.micro"

    def test_create_params_extracted(self):
        result = engine.detect("crée une VM Ubuntu sur AWS en eu-west-1")
        assert result.params.get("provider") == "aws"
        assert result.params.get("os") == "ubuntu"
        assert result.params.get("region") == "eu-west-1"

    def test_create_missing_provider(self):
        result = engine.detect("crée une instance ubuntu")
        assert "provider (aws/azure/gcp)" in result.missing_params

    def test_create_missing_os(self):
        result = engine.detect("crée une VM sur AWS")
        assert "os (ubuntu/centos/debian)" in result.missing_params


# ─────────────────────────────────────────────────────────────────────────────
# Intent: configure
# ─────────────────────────────────────────────────────────────────────────────

class TestConfigureIntent:
    def test_install_nginx(self):
        assert_intent("installe nginx sur mon serveur", "configure")

    def test_configure_ufw(self):
        assert_intent("configure le firewall ufw", "configure")

    def test_setup_docker(self):
        assert_intent("setup docker sur la machine", "configure")

    def test_install_english(self):
        assert_intent("install mysql on the server", "configure")

    def test_catalog_action_id_nginx(self):
        result = engine.detect("installe nginx")
        assert result.intent == "configure"
        assert result.action_id == "install_nginx"

    def test_catalog_action_id_docker(self):
        result = engine.detect("installer docker")
        assert result.intent == "configure"
        assert result.action_id == "install_docker"

    def test_services_extracted(self):
        result = engine.detect("installe nginx et docker sur mon serveur")
        assert "nginx" in result.params.get("services", [])
        assert "docker" in result.params.get("services", [])


# ─────────────────────────────────────────────────────────────────────────────
# Intent: audit
# ─────────────────────────────────────────────────────────────────────────────

class TestAuditIntent:
    def test_audit_securite(self):
        assert_intent("fais un audit de sécurité", "audit")

    def test_scanner(self):
        assert_intent("scanner les vulnérabilités du serveur", "audit")

    def test_lynis(self):
        assert_intent("lance lynis sur la machine", "audit")

    def test_hardening(self):
        assert_intent("je veux durcir la configuration ssh", "audit")

    def test_security_english(self):
        assert_intent("run a security audit", "audit")


# ─────────────────────────────────────────────────────────────────────────────
# Intent: monitoring
# ─────────────────────────────────────────────────────────────────────────────

class TestMonitoringIntent:
    def test_monitoring_keyword(self):
        assert_intent("je veux du monitoring sur mon serveur", "monitoring")

    def test_metriques(self):
        assert_intent("affiche les métriques CPU et RAM", "monitoring")

    def test_grafana(self):
        assert_intent("installe grafana pour surveiller mes machines", "monitoring")

    def test_prometheus(self):
        # "configure" is the explicit action verb → configure wins over monitoring on equal score
        assert_intent("configure prometheus", "configure")

    def test_uptime(self):
        assert_intent("vérifie l'uptime du serveur", "monitoring")


# ─────────────────────────────────────────────────────────────────────────────
# Intent: check_status
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckStatusIntent:
    def test_status_service(self):
        assert_intent("quel est le statut du service nginx ?", "check_status")

    def test_tourne(self):
        assert_intent("est-ce que nginx tourne ?", "check_status")

    def test_lister_instances(self):
        assert_intent("lister les instances disponibles", "check_status")

    def test_voir_ressources(self):
        assert_intent("afficher les ressources AWS", "check_status")


# ─────────────────────────────────────────────────────────────────────────────
# Intent: explain_error
# ─────────────────────────────────────────────────────────────────────────────

class TestExplainErrorIntent:
    def test_connection_refused(self):
        assert_intent("j'ai l'erreur connection refused, c'est quoi ?", "explain_error")

    def test_permission_denied(self):
        assert_intent("permission denied quand je lance mon script", "explain_error")

    def test_erreur_keyword(self):
        assert_intent("j'ai une erreur dans mes logs, peux-tu m'aider ?", "explain_error")

    def test_pourquoi_plante(self):
        assert_intent("pourquoi ça plante sur mon serveur ?", "explain_error")

    def test_exit_code(self):
        assert_intent("mon script retourne exit code 1, que faire ?", "explain_error")

    def test_exception(self):
        assert_intent("j'ai une exception: null pointer, c'est grave ?", "explain_error")


# ─────────────────────────────────────────────────────────────────────────────
# Intent: generate_config
# ─────────────────────────────────────────────────────────────────────────────

class TestGenerateConfigIntent:
    def test_generer_terraform(self):
        assert_intent("génère un fichier terraform pour une VM AWS", "generate_config")

    def test_creer_config_nginx(self):
        assert_intent("crée un fichier de config nginx pour un reverse proxy", "generate_config")

    def test_ansible_playbook(self):
        assert_intent("génère un playbook ansible pour installer nginx", "generate_config")

    def test_montre_config(self):
        assert_intent("montre-moi un exemple de configuration docker", "generate_config")

    def test_config_type_extracted(self):
        result = engine.detect("génère un template terraform")
        assert result.intent == "generate_config"
        assert "terraform" in result.params.get("config_type", [])


# ─────────────────────────────────────────────────────────────────────────────
# Intent: help
# ─────────────────────────────────────────────────────────────────────────────

class TestHelpIntent:
    def test_aide(self):
        assert_intent("aide", "help")

    def test_comment_utiliser_dac(self):
        assert_intent("comment utiliser dac ?", "help")

    def test_quest_ce_que(self):
        assert_intent("qu'est-ce que DAC peut faire ?", "help")

    def test_tutoriel(self):
        assert_intent("tu as un tutoriel pour démarrer ?", "help")


# ─────────────────────────────────────────────────────────────────────────────
# Intent: unknown
# ─────────────────────────────────────────────────────────────────────────────

class TestUnknownIntent:
    def test_empty_string(self):
        result = engine.detect("")
        assert result.intent == "unknown"
        assert result.action == "none"

    def test_gibberish(self):
        result = engine.detect("azerty qsdfgh poiuyt")
        assert result.intent == "unknown"

    def test_unknown_has_suggestions(self):
        result = engine.detect("blabla xyz")
        assert result.intent == "unknown"
        assert result.suggestions is not None
        assert len(result.suggestions) > 0

    def test_unknown_confidence_zero(self):
        result = engine.detect("zxcvbnm")
        assert result.confidence == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Action mapping
# ─────────────────────────────────────────────────────────────────────────────

class TestActionMapping:
    def test_create_maps_to_create(self):
        result = engine.detect("crée une instance ubuntu")
        assert result.action == "create"

    def test_configure_maps_to_configure(self):
        result = engine.detect("installe nginx")
        assert result.action == "configure"

    def test_audit_maps_to_audit(self):
        result = engine.detect("fais un audit de sécurité")
        assert result.action == "audit"

    def test_monitoring_maps_to_monitoring(self):
        result = engine.detect("je veux du monitoring")
        assert result.action == "monitoring"

    def test_help_maps_to_free_chat(self):
        result = engine.detect("aide")
        assert result.action == "free_chat"

    def test_explain_error_maps_to_free_chat(self):
        result = engine.detect("j'ai une erreur connection refused")
        assert result.action == "free_chat"

    def test_unknown_maps_to_none(self):
        result = engine.detect("azerty qsdfgh")
        assert result.action == "none"


# ─────────────────────────────────────────────────────────────────────────────
# to_legacy_dict compatibility
# ─────────────────────────────────────────────────────────────────────────────

class TestLegacyDict:
    def test_has_required_fields(self):
        result = engine.detect("crée une instance ubuntu sur aws")
        d = result.to_legacy_dict()
        assert "action" in d
        assert "description" in d
        assert "extracted_params" in d
        assert "missing_params" in d
        assert "confidence_score" in d

    def test_extracted_params_is_dict(self):
        result = engine.detect("crée une VM ubuntu sur aws")
        d = result.to_legacy_dict()
        assert isinstance(d["extracted_params"], dict)

    def test_missing_params_is_list(self):
        result = engine.detect("crée une instance")
        d = result.to_legacy_dict()
        assert isinstance(d["missing_params"], list)


# ─────────────────────────────────────────────────────────────────────────────
# Module-level detect_intent function
# ─────────────────────────────────────────────────────────────────────────────

class TestModuleFunction:
    def test_detect_intent_convenience(self):
        result = detect_intent("installe docker")
        assert result.intent == "configure"
        assert result.action == "configure"
