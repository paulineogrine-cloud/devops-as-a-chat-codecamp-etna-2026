# Challenge 2 — Amélioration de la détection des intentions

## Piste choisie : moteur hybride règles/regex

### Problèmes identifiés sur la base de code existante

Avant ce challenge, la détection d'intentions était fragmentée sur **4 fichiers distincts** qui se chevauchaient et se contredisaient parfois :

| Fichier | Rôle (avant) |
|---------|-------------|
| `intent_detector.py` | Détection spécialisée Ubuntu + services (regex ad hoc) |
| `detect_intent_catalog.py` | Détection keyword + catalogue |
| `chat_service.py` | Orchestration : Ubuntu → service → GPT → fallback manuel |
| `gpt_service.py` | Appel OpenAI + fallback keyword |

En plus :
- Seulement 5 intentions reconnues (`create`, `configure`, `audit`, `monitoring`, `free_chat`)
- L'extraction de paramètres était dupliquée 3 fois dans des versions légèrement différentes
- Les intentions inconnues tombaient silencieusement en `"none"` sans suggestion
- Aucun test

---

## Architecture retenue

### Approche hybride sans IA (2 couches)

```
Message utilisateur
        │
        ▼
 ┌─────────────────────────────────┐
 │  Couche 1 — Règles / Regex      │
 │  • Scoring keywords (1.0 pt)    │
 │  • Scoring patterns (1.5 pt)    │
 │  • Déduplication normalisée     │
 │  → confidence = 0.45 + s×0.12  │
 └───────────────┬─────────────────┘
                 │  intent = "configure" ?
                 ▼
 ┌─────────────────────────────────┐
 │  Couche 2 — Catalogue           │
 │  • match_config_action()        │
 │  → action_id = "install_nginx"  │
 └───────────────┬─────────────────┘
                 │
                 ▼
           IntentResult
```

**Pourquoi sans IA ?**
- 100 % déterministe → testable unitairement
- Pas de latence réseau ni de clé API requise
- Le fallback GPT existant dans `chat_service.py` reste disponible pour la génération de code/config

---

## Fichiers créés ou modifiés

### Créés

| Fichier | Description |
|---------|-------------|
| `devops_api/app/services/intent_engine.py` | Moteur hybride unifié (nouveau) |
| `devops_api/tests/__init__.py` | Package tests |
| `devops_api/tests/test_intent_engine.py` | 60 tests unitaires |

### Modifiés

| Fichier | Changement |
|---------|-----------|
| `devops_api/app/schemas/intent_schema.py` | Ajout de `SUPPORTED_INTENTS`, `missing_params`, `suggestions`, `is_unknown()` dans `DetectedIntent` |
| `devops_api/app/services/chat_service.py` | `detect_intent_and_action()` délègue au nouveau moteur via `detect_intent()` |

---

## Taxonomie des intentions (étendue de 5 à 10)

| Intention | Exemples utilisateur | Action DevOps |
|-----------|---------------------|---------------|
| `create` | "crée une VM Ubuntu sur AWS" | `create_infrastructure` |
| `configure` | "installe nginx sur mon serveur" | `configure_service` |
| `audit` | "lance un audit de sécurité avec lynis" | `run_audit` |
| `monitoring` | "configure prometheus pour mes métriques" | `check_metrics` |
| `check_status` | "est-ce que nginx tourne ?" | `check_resource_status` |
| `explain_error` | "pourquoi j'ai permission denied ?" | `free_chat` |
| `generate_config` | "génère un template Terraform pour AWS" | `generate_config_file` |
| `help` | "comment utiliser DAC ?" | `free_chat` |
| `free_chat` | conversation libre | `free_chat` |
| `unknown` | intention non reconnue | `ask_clarification` |

---

## Extraction de paramètres

Le moteur extrait automatiquement les paramètres depuis le message :

| Paramètre | Exemples reconnus |
|-----------|------------------|
| `provider` | `aws`, `azure`, `gcp` |
| `os` | `ubuntu`, `centos`, `debian`, `windows` |
| `instance_type` | `t2.micro`, `t3.small`, `t3a.medium` |
| `region` | `eu-west-1`, `us-east-1`, `ap-southeast-1` |
| `port` | `port 443`, `port 8080` |
| `services` | `nginx`, `docker`, `mysql`, `redis`, `prometheus`… |
| `config_type` | `terraform`, `ansible`, `dockerfile`, `kubernetes` |

---

## Gestion des intentions inconnues

Quand aucune règle ne dépasse le seuil de confiance (0.40), le moteur retourne une `IntentResult` avec :
- `intent = "unknown"`, `action = "none"`, `confidence = 0.0`
- `suggestions` : 3–4 exemples de demandes que DAC sait traiter

Exemple de réponse pour un message incompréhensible :
```json
{
  "intent": "unknown",
  "action": "none",
  "confidence": 0.0,
  "description": "Je n'ai pas compris votre demande. Voici quelques exemples:",
  "suggestions": [
    "Créer/provisionner une infrastructure cloud (VM, réseau, etc.)",
    "Configurer ou installer un service sur une machine existante",
    "Auditer la sécurité d'une machine ou d'une infrastructure"
  ]
}
```

---

## Formule de confiance

```python
confidence = min(0.45 + score × 0.12, base_confidence)
```

| Score | Exemple | Confiance |
|-------|---------|-----------|
| 1.0 | 1 keyword match | 0.57 |
| 1.5 | 1 pattern match | 0.63 |
| 2.0 | 2 keywords | 0.69 |
| 2.5 | 2 keywords + 1 pattern | 0.75 |
| 3.0 | 3 keywords | 0.81 |

Tout score > 0 dépasse le seuil de 0.40. La déduplication des keywords normalisés empêche l'inflation artificielle du score quand plusieurs variantes d'un mot sont dans la liste (ex. "créer", "creer", "crée" → tous normalisés en "cree").

---

## Lancer les tests

```bash
cd devops_api
pip install pytest
pytest tests/test_intent_engine.py -v
```

Résultat attendu : **60 passed** en < 1 seconde, sans clé OpenAI, sans base de données.

```
======================== 60 passed in 0.10s ==============================
```

---

## Compatibilité ascendante

`detect_intent_and_action()` dans `chat_service.py` retourne toujours le même format dict attendu par `chat_creation_routes.py` :

```python
{
    "action":           "create|configure|audit|monitoring|free_chat|none",
    "description":      "...",
    "extracted_params": {...},
    "missing_params":   [...],
    "confidence_score": 0.85,
    # champs enrichis pour les nouveaux consommateurs :
    "intent":           "create",
    "action_id":        "install_nginx",
    "matched_keywords": [...],
    "suggestions":      None
}
```

---

## Décisions techniques

- **Pas d'IA dans la couche de détection** : l'appel GPT existant (`generate_instructions_from_gpt`) reste pour la *génération* de code Terraform/Ansible, pas pour la détection.
- **Couche catalogue conservée** : `config_catalog.py` est réutilisée en couche 2 pour résoudre `install_nginx` depuis `configure`, sans duplication.
- **Priorité par spécificité** : en cas d'égalité de score, l'ordre `explain_error > generate_config > create > configure > audit > monitoring > check_status > help` garantit que l'intention la plus précise l'emporte.
- **Normalisation unicode** : les accents sont supprimés avant matching pour couvrir les fautes de frappe sans accent.
