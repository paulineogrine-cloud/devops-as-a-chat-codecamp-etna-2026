# Challenge 5 — Amélioration des logs et du suivi temps réel

## Challenge choisi

**Challenge 5 — Amélioration des logs et du suivi temps réel**

Objectif : améliorer l'observabilité de DAC (DevOps As a Chat) en rendant les logs lisibles, structurés, corrélés entre eux, et visibles en temps réel dans l'interface utilisateur.

---

## Problème identifié

Avant ce challenge, le projet souffrait de plusieurs lacunes d'observabilité :

| Problème | Manifestation |
|---|---|
| Logs non structurés | Sortie console brute, mélange de formats, impossible à parser |
| Niveaux de log incohérents | Des traces de debug internes s'affichaient au niveau `INFO`, noyant les événements métier |
| Pas de corrélation | Impossible de relier un message utilisateur, son intention détectée et l'action déclenchée |
| Pas de suivi temps réel | L'utilisateur ne savait pas ce qui se passait pendant l'exécution d'une action (create, configure, suppression...) |
| Erreurs 500 opaques | Un crash renvoyait un message générique, sans identifiant pour retrouver la cause dans les logs |
| Flows sans logs | Les actions `configure`, `ssm status`, `vpc status`, `liste des ressources` et `supprimer` ne produisaient aucun log d'exécution visible dans l'UI |

---

## Solution proposée

La solution est décomposée en **6 étapes techniques** correspondant aux 6 premières `feat(logs):` de la branche, plus des correctifs de wiring pour connecter les logs à l'interface.

### Étape 1 — Logger JSON structuré centralisé

**Fichier :** `devops_api/app/utils/logging_utils.py`

Un `JSONFormatter` Python émettant chaque log en une seule ligne JSON parseable :

```json
{"ts": "2026-06-10T09:29:11+00:00", "level": "INFO", "logger": "app.routes.chat_creation_routes", "msg": "Intention détectée: create"}
```

La fonction `setup_logging(level)` configure le logger root une fois au démarrage (`main.py`) ; tous les modules héritent automatiquement de ce handler. Le niveau est piloté par la variable d'environnement `DAC_LOG_LEVEL` (ou `LOG_LEVEL` pour compatibilité).

### Étape 2 — Niveaux de logs cohérents

**Fichiers :** `devops_api/app/security/audit_logger.py`, `devops_api/app/services/execution_logger.py`, `devops_api/app/services/chat_service.py`

Reclassement des logs selon leur nature réelle :

- `DEBUG` : traces internes (démarrage de session, sauvegarde d'un log en base, détection d'intention brute)
- `INFO` : événements métier significatifs (intention détectée, exécution lancée)
- `WARNING` : anomalie non bloquante (instance introuvable, crédentiels partiels)
- `ERROR` : erreur bloquante avec stack trace

Passage au style `%` pour les messages (`logger.info("foo %s", bar)`) pour éviter les f-strings calculés avant que le filtre de niveau n'entre en jeu.

### Étape 3 — Corrélation message → intention → action

**Fichiers :** `devops_api/app/core/context.py`, `devops_api/app/main.py`, `devops_api/migrations/versions/add_level_and_correlation_to_execution_logs.py`

Un `ContextVar[str]` nommé `correlation_id_var` stocke un UUID v4 par requête HTTP. Ce UUID est :

1. Généré par un middleware FastAPI à chaque requête entrante
2. Injecté automatiquement dans chaque ligne de log JSON par `JSONFormatter`
3. Persisté dans la colonne `correlation_id` de la table `execution_logs`
4. Exposé dans les réponses d'erreur `ErrorResponse`

Cela permet de retrouver dans les logs server-side tous les événements liés à un message utilisateur précis, en filtrant par `correlation_id`.

**Migration Alembic** (`revision: a1b2c3d4e5f6`) : ajout des colonnes `level VARCHAR(16)` et `correlation_id VARCHAR(64)` + index sur `correlation_id` dans `execution_logs`.

### Étape 4 — Endpoint de polling temps réel

**Fichier :** `devops_api/app/routes/executions_routes.py`

Nouvel endpoint :

```
GET /executions/{execution_id}/logs?since=<ISO8601>&limit=<1-500>
```

- Retourne les logs triés par `created_at` croissant
- Le paramètre `since` permet de ne récupérer que les nouveaux logs (polling incrémental)
- Retourne 404 si l'exécution n'appartient pas à l'utilisateur courant
- Chaque entrée expose : `id`, `event`, `level`, `message`, `correlation_id`, `created_at`

### Étape 5 — Affichage progressif côté frontend

**Fichiers :** `frontend/src/hooks/useExecutionLogs.ts`, `frontend/src/components/Chat/ExecutionLogList.tsx`, `frontend/src/components/TaskProgress.tsx`, `frontend/src/pages/Chat.tsx`

**`useExecutionLogs`** : hook React qui poll `GET /executions/{id}/logs` toutes les 2 secondes, en passant `since` = `created_at` du dernier log reçu. S'arrête automatiquement quand `done = true`.

**`ExecutionLogList`** : composant MUI affichant les logs avec :
- Icône colorée par niveau : 🔘 DEBUG / 🔵 INFO / 🟠 WARNING / 🔴 ERROR
- Auto-scroll vers le bas à chaque nouveau log
- Collapse/expand via bouton
- Police monospace, hauteur maximale fixée à 280px avec défilement

**Wiring dans `Chat.tsx`** : quand le backend retourne `execution_id_db` dans `data.extra`, le frontend appelle `setCurrentExecutionId(execution_id_db)` qui déclenche le polling.

### Étape 6 — Erreurs enrichies avec correlation_id

**Fichiers :** `devops_api/app/schemas/error_schema.py`, `devops_api/app/main.py`

`ErrorResponse` expose désormais le champ `correlation_id` (nullable). La fonction `make_error()` lit automatiquement le `ContextVar`. L'exception handler global (`500`) inclut le `correlation_id` dans le corps JSON et dans le log d'erreur serveur, permettant de relier immédiatement un crash visible côté client à sa cause dans les logs.

### Correctifs de wiring — Logs pour tous les flows

**Fichier :** `devops_api/app/routes/chat_creation_routes.py`

Chaque flow conversationnel crée maintenant un enregistrement `models.Execution` et appelle `log_execution_event()` pour tracer les étapes clés. L'`execution_id` est retourné au frontend via `send_bot_message(..., extra={"execution_id_db": execution.id})`.

| Flow | task_type | Événements tracés |
|---|---|---|
| `create` (Terraform) | `terraform` | started → phase (génération) → phase (apply) → completed / failed |
| `configure` (Ansible) | `ansible` | started → phase (playbook) → completed / failed |
| `audit` | `audit` | started → phase → completed / failed |
| `monitoring` | `monitoring` | started → phase → completed / failed |
| `ssm status` | `ssm_status` | started → completed / failed |
| `vpc status` | `vpc_status` | started → completed / failed |
| `liste des ressources` | `list_resources` | started → completed / failed |
| `supprimer` | `delete_instances` | started → phase (par instance) → completed / failed |

---

## Procédure d'installation

### Prérequis

- Docker ≥ 24
- Docker Compose ≥ 2.20
- Git

### Installation

```bash
git clone <url-du-repo>
cd devops-as-a-chat-codecamp-etna-2026
git checkout challenge5

cp .env.example .env
# Éditer .env si besoin (voir section Variables d'environnement)

docker compose build
docker compose up -d
```

La migration Alembic (`a1b2c3d4e5f6`) s'exécute automatiquement au démarrage du backend et ajoute les colonnes `level` et `correlation_id` à la table `execution_logs`.

---

## Procédure de lancement

```bash
# Démarrer tous les services
docker compose up -d

# Accéder à l'interface
open http://localhost:5173

# Voir les logs du backend en temps réel (format JSON structuré)
docker compose logs -f backend

# Exemple de filtre par correlation_id
docker compose logs backend | grep '"correlation_id": "abc-123"'
```

Pour appliquer des modifications Python au backend (code baked dans l'image) :

```bash
docker compose build backend
docker compose up -d backend
```

---

## Variables d'environnement

| Variable | Valeur par défaut | Description |
|---|---|---|
| `DAC_LOG_LEVEL` | `debug` | Niveau de log du backend (`debug`, `info`, `warning`, `error`) |
| `LOG_LEVEL` | — | Alias accepté pour compatibilité |
| `DATABASE_URL` | `postgresql://dac:dac@postgres:5432/devops_api_db` | Connexion PostgreSQL |
| `SECRET_KEY` | `change-this-secret-key-for-local-dev` | Clé JWT — à changer en production |
| `FERNET_KEY` | voir `.env.example` | Clé de chiffrement des secrets AWS |
| `DAC_AI_PROVIDER` | `mistral` | Fournisseur IA (`mistral` ou `openai`) |
| `MISTRAL_API_KEY` | — | Clé API Mistral (optionnelle, le MVP fonctionne sans) |
| `OPENAI_API_KEY` | — | Clé API OpenAI (optionnelle) |
| `VITE_API_URL` | `http://localhost:8000` | URL du backend pour le frontend |

Aucune clé API n'est codée en dur dans le code source. Toutes les valeurs sensibles transitent par des variables d'environnement ou sont chiffrées via Fernet avant stockage en base.

---

## Choix techniques

### Pourquoi JSON structuré ?

Les logs textuels libres sont difficiles à filtrer, à agréger et à envoyer vers un système centralisé (Loki, Datadog, ELK). Le format JSON one-line est parseable directement par `jq`, par n'importe quel log shipper, et reste lisible humainement.

### Pourquoi `ContextVar` pour le `correlation_id` ?

FastAPI est async ; `threading.local` ne fonctionnerait pas correctement dans ce contexte. `ContextVar` est thread-safe et async-safe : chaque coroutine ou thread a son propre slot d'exécution. L'injection dans le `JSONFormatter` est transparente — aucun module n'a besoin de passer le `correlation_id` explicitement.

### Pourquoi le polling plutôt que WebSocket ?

Le polling toutes les 2 secondes avec un paramètre `since` incrémental est suffisant pour le cas d'usage (les actions durent en général entre 5 et 60 secondes). Il évite la complexité d'un WebSocket (gestion de reconnexion, authentification différente, état serveur). Le paramètre `since` garantit qu'on ne re-télécharge jamais les mêmes logs.

### Pourquoi `log_execution_event` directement, sans `run_execution_by_id` ?

Les flows conversationnels (`chat_creation_routes.py`) ne passent pas par le service d'exécution asynchrone (`run_execution_by_id`) — ils s'exécutent de façon synchrone dans le handler HTTP. Appeler `log_execution_event` directement est donc la seule approche possible sans refactoring majeur du pipeline.

---

## Limites connues

- **Suppression d'instance** : l'endpoint `DELETE /resources/delete_instance` retourne 404 si l'instance n'a pas d'entrée dans la table `providers` avec des crédentials chiffrés. Ce n'est pas un bug introduit par ce challenge — les logs affichent correctement l'erreur en `WARNING`, et l'exécution passe en `failed`.

- **Pas de streaming serveur** : les logs arrivent par polling. Un délai de jusqu'à 2 secondes est possible entre la production d'un log et son affichage.

- **Volume de logs** : l'endpoint de polling est limité à 500 logs par appel. Pour des exécutions très longues produisant plus de 500 entrées, les premiers logs pourraient être manqués si `since` n'est pas utilisé correctement.

- **Rétention** : les logs d'exécution restent en base indéfiniment. Il n'y a pas de politique d'expiration.

---

## Pistes d'amélioration

- **Server-Sent Events (SSE)** : remplacer le polling par un flux SSE pour une latence quasi-nulle sans la complexité d'un WebSocket.
- **Centralisation des logs** : envoyer les lignes JSON vers un stack Loki + Grafana ou Datadog pour de la recherche full-text et des dashboards.
- **Politique de rétention** : un job périodique pour archiver ou supprimer les `execution_logs` de plus de N jours.
- **Sampling DEBUG** : en production, activer le niveau `INFO` et ne passer en `DEBUG` qu'à la demande (via changement de `DAC_LOG_LEVEL` sans redémarrage, en utilisant un endpoint admin).
- **Traces distribuées** : intégrer OpenTelemetry pour propager le `correlation_id` jusque dans les appels Terraform/Ansible subprocess.

---

## Fichiers modifiés

| Fichier | Nature de la modification |
|---|---|
| `devops_api/app/utils/logging_utils.py` | Ajout de `JSONFormatter`, `setup_logging()`, `get_logger()` |
| `devops_api/app/main.py` | Remplacement de `basicConfig` par `setup_logging()` ; handler global 500 avec `correlation_id` |
| `devops_api/app/core/context.py` | Nouveau fichier — `ContextVar` pour le `correlation_id` |
| `devops_api/app/services/execution_logger.py` | Ajout persistance `level` et `correlation_id` dans `log_execution_event` |
| `devops_api/app/security/audit_logger.py` | Reclassement des traces internes en `DEBUG` |
| `devops_api/app/services/chat_service.py` | Reclassement des traces de détection en `DEBUG` |
| `devops_api/app/schemas/error_schema.py` | `ErrorResponse` expose `correlation_id` |
| `devops_api/app/routes/executions_routes.py` | Nouvel endpoint `GET /executions/{id}/logs` |
| `devops_api/app/routes/chat_creation_routes.py` | Logs d'exécution pour tous les flows conversationnels ; nouveaux handlers `vpc_status`, `deletion_mode`, `awaiting_delete_confirmation` |
| `devops_api/app/models/execution_log.py` | Ajout colonnes `level` et `correlation_id` sur le modèle SQLAlchemy |
| `devops_api/migrations/versions/add_level_and_correlation_to_execution_logs.py` | Migration Alembic `a1b2c3d4e5f6` |
| `devops_api/app/settings.py` | Lecture de `DAC_LOG_LEVEL` |
| `docker-compose.yml` | Exposition de `DAC_LOG_LEVEL` au service backend |
| `.env.example` | Ajout de `DAC_LOG_LEVEL=debug` |
| `frontend/src/hooks/useExecutionLogs.ts` | Nouveau hook — polling incrémental des logs d'exécution |
| `frontend/src/hooks/useExecutionPolling.ts` | Exposition de `executionLogs` depuis `useExecutionLogs` |
| `frontend/src/components/Chat/ExecutionLogList.tsx` | Nouveau composant — liste de logs avec icônes par niveau |
| `frontend/src/components/TaskProgress.tsx` | Intégration de `ExecutionLogList` |
| `frontend/src/pages/Chat.tsx` | Extraction de `execution_id_db` depuis `data.extra` → `setCurrentExecutionId` |
| `frontend/src/api/axiosClient.ts` | Ajout de l'en-tête `X-Correlation-ID` dans les requêtes |

---

## Démonstration

1. Démarrer l'application (`docker compose up -d`)
2. Se connecter sur `http://localhost:5173`
3. Créer une session et configurer des crédentials AWS valides
4. Taper l'un des messages suivants dans le chat :
   - `"créer une instance nginx"` → flow **create** avec logs Terraform
   - `"configure nginx"` → flow **configure** avec logs Ansible
   - `"ssm status"` → flow **ssm status**
   - `"vpc status"` → flow **vpc status**
   - `"liste des ressources"` → flow **list resources**
   - `"supprimer"` → flow **delete** avec logs par instance
5. Observer le composant **Logs d'exécution** qui apparaît dans le chat et se met à jour en temps réel

Pour corréler un log visible dans l'UI avec les logs serveur :
```bash
# Trouver le correlation_id dans les logs d'exécution (UI)
# Puis filtrer côté serveur :
docker compose logs backend | python3 -c "
import sys, json
cid = 'COLLER_CORRELATION_ID_ICI'
for line in sys.stdin:
    try:
        obj = json.loads(line)
        if obj.get('correlation_id') == cid:
            print(line.strip())
    except Exception:
        pass
"
```
