# Feature : Analyse IA des logs d'exécution (AI Summary Bubble)

## Objectif

Après chaque exécution Terraform/Ansible, afficher automatiquement dans le chat une bulle d'analyse IA qui explique ce qui s'est passé (succès, erreur, suggestion de correction), générée par GPT-4o.

---

## Architecture du flux complet

```
[User déclenche Terraform]
        │
        ▼
[Backend crée AsyncTask + Execution en DB]
        │
        ▼
[run_execution_by_id() exécute Terraform]
        │ retourne { ..., execution_id: X }        ← FIX 3
        ▼
[_mark_task_completed() sauvegarde execution_id]   ← FIX 4
        │ async_task.execution_id = X en DB
        ▼
[Frontend poll GET /async/tasks/{taskId}/status]
        │ reçoit execution_id: X (non-null)        ← était toujours null avant
        ▼
[useTaskPolling détecte execution_id → appelle]
[GET /executions/X?analyze=true]                   ← FIX 1 + FIX 2
        │ retourne ai_summary: { status, summary, fix }
        ▼
[executionIdRef.current = X (synchrone)]           ← FIX 5
        │
        ▼
[onFinished(executionId, status) → AiSummaryBubble s'affiche]
```

---

## Modifications Backend

### FIX 1 — Nouvelle fonction IA dans `gpt_service.py`

**Fichier** : `devops_api/app/services/gpt_service.py`

**Problème** : Aucune fonction pour analyser les logs d'exécution avec GPT.

**Ajout** en fin de fichier :
```python
async def analyze_execution_logs(logs: list[str], engine: str) -> dict:
    """Analyse les logs Terraform/Ansible avec GPT et retourne status/summary/fix."""
    joined = "\n".join(logs[-100:])
    messages = [
        {
            "role": "system",
            "content": (
                f"Tu es un expert DevOps. Analyse ces logs d'exécution {engine} "
                "et réponds UNIQUEMENT en JSON valide avec exactement ces 3 clés : "
                "\"status\" (\"success\", \"error\" ou \"warning\"), "
                "\"summary\" (résumé clair en français en 2-3 phrases), "
                "\"fix\" (suggestion de correction si erreur, sinon null)."
            ),
        },
        {"role": "user", "content": joined},
    ]
    if AI_PROVIDER != "openai" or client is None:
        return {"status": "warning", "summary": "Mode IA mock actif.", "fix": None}
    raw = _chat_with_retry(messages, model=_DEFAULT_MODEL, temperature=0.1)
    try:
        return json.loads(_strip_code_fences(raw))
    except (json.JSONDecodeError, ValueError):
        return {"status": "warning", "summary": raw[:500], "fix": None}
```

---

### FIX 2 — Nouveau service wrapper `log_analyzer_service.py`

**Fichier** : `devops_api/app/services/log_analyzer_service.py` *(créé)*

**Problème** : Pas de service dédié avec auto-détection du moteur (Terraform vs Ansible).

```python
from app.services.gpt_service import analyze_execution_logs

def _detect_engine(logs: list[str]) -> str:
    joined = "\n".join(logs[:20]).lower()
    if "ansible" in joined or "play recap" in joined or "task [" in joined:
        return "ansible"
    return "terraform"

async def analyze_logs(logs: list[str], engine: str | None = None) -> dict:
    detected = engine or _detect_engine(logs)
    result = await analyze_execution_logs(logs, detected)
    return {
        "status": result.get("status", "warning"),
        "summary": result.get("summary", "Analyse non disponible."),
        "fix": result.get("fix", None),
    }
```

---

### FIX 3 — Route `GET /executions/{id}` enrichie

**Fichier** : `devops_api/app/routes/executions_routes.py`

**Problème** : La route ne supportait pas l'analyse IA et retournait toujours `ai_summary: null`.

**Changements** :
- Route rendue `async`
- Paramètre query `?analyze=true` ajouté
- Champ `ai_summary` ajouté à la réponse

```python
@router.get("/executions/{execution_id}", tags=["Executions"])
async def get_execution(
    execution_id: int,
    analyze: bool = Query(False),   # ← nouveau
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    # ...
    ai_summary = None
    if analyze and logs:
        from app.services.log_analyzer_service import analyze_logs
        ai_summary = await analyze_logs(logs, execution.task_type)

    return {
        # ...tous les champs existants...
        "ai_summary": ai_summary,   # ← nouveau
    }
```

**Test Postman** : `GET {{base_url}}/executions/87?analyze=true`

---

### FIX 4 — Liaison `AsyncTask.execution_id` en base

**Problème** : Le champ `AsyncTask.execution_id` existait dans le modèle SQLAlchemy mais **n'était jamais écrit** → le frontend recevait toujours `execution_id: null` depuis `/async/tasks/{taskId}/status`.

**Fichier 1** : `devops_api/app/services/execution_handlers.py`

`run_execution_by_id()` inclut maintenant son propre ID dans le résultat :
```python
# Avant (à la fin de run_execution_by_id) :
return result

# Après :
if isinstance(result, dict):
    result["execution_id"] = execution_id
else:
    result = {"execution_id": execution_id}
return result
```

**Fichier 2** : `devops_api/app/services/task_manager.py`

`_mark_task_completed()` persiste l'ID en base :
```python
# Après la sérialisation du result_data, ajouter :
if isinstance(result, dict) and result.get("execution_id"):
    async_task.execution_id = result["execution_id"]
```

---

## Modifications Frontend

### FIX 5 — Timing React dans `useTaskPolling.ts` + `TaskProgress.tsx`

**Fichier** : `frontend/src/hooks/useTaskPolling.ts`

**Problème** : `execution_id` est reçu du backend et stocké via `setTaskStatus()` (état React asynchrone). Mais `onComplete` est appelé dans le même tick JavaScript, **avant** que React re-rende. Donc `executionId` dans la closure est encore `undefined`.

**Fix** : Ajout d'un `ref` mis à jour **synchronement** avant les callbacks :
```ts
const executionIdRef = useRef<number | undefined>(undefined);

// Dans pollTaskStatus, avant setTaskStatus() :
if (status.execution_id) {
    executionIdRef.current = status.execution_id;  // synchrone !
}
setTaskStatus(status);  // async (batché par React)

// Exposé dans le return :
executionIdRef,
```

**Fichier** : `frontend/src/components/TaskProgress.tsx`

Utilise le ref (toujours à jour) plutôt que la valeur React (stale) :
```ts
const { ..., executionId, executionIdRef } = useTaskPolling(taskId, {
    onComplete: (result) => {
        onFinished(executionIdRef.current ?? executionId, 'completed');
    },
    onError: (err) => {
        onFinished(executionIdRef.current ?? executionId, 'failed');
    },
});
```

---

### FIX 6 — `AiSummaryBubble.tsx` appelle `?analyze=true`

**Fichier** : `frontend/src/components/Chat/AiSummaryBubble.tsx`

**Problème** : Le composant appelait `GET /executions/${executionId}` sans le paramètre `?analyze=true`, donc recevait toujours `ai_summary: null`.

```ts
// Avant :
axiosClient.get(`/executions/${executionId}`)

// Après :
axiosClient.get(`/executions/${executionId}?analyze=true`)
```

---

## Prérequis

| Variable d'environnement | Valeur requise |
|--------------------------|----------------|
| `OPENAI_API_KEY`         | Clé API OpenAI valide |
| `DAC_AI_PROVIDER`        | `openai` (défaut: `mock` si pas de clé) |

> En mode `mock`, la bulle apparaît mais affiche *"Mode IA mock actif"* au lieu d'une vraie analyse.

---

## Résultat attendu

Après une exécution Terraform/Ansible réussie ou échouée, une bulle apparaît dans le chat avec :

- **Statut** : `success` / `warning` / `error` (icône + couleur)
- **Résumé** : 2-3 phrases expliquant ce qui s'est passé (en français)
- **Suggestion** : Si erreur, une piste de correction concrète
- **Bouton fermer** : La bulle est dismissible
