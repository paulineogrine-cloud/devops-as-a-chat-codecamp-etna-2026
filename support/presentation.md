# Soutenance - DAC Code Camp ETNA 2026

## 1. Sujet

DAC signifie DevOps-as-a-Chat. Le projet permet de piloter des actions DevOps via une interface conversationnelle.

## 2. Challenge choisi

Challenge 5: amelioration des logs et du suivi temps reel.

Choix personnel: rendre DAC observable, comprendre ce qui se passe pendant une action cloud, et pouvoir diagnostiquer une erreur sans fouiller les logs serveur a la main.

## 3. Probleme initial

- Les logs backend etaient du texte brut non parseable.
- Les niveaux DEBUG/INFO etaient melanges, les evenements metier noyes dans le bruit.
- Aucune correlation entre un message utilisateur, l'intention detectee et l'action declenchee.
- L'utilisateur ne voyait rien pendant l'execution d'une action (create, configure, suppression...).
- Un crash 500 renvoyait un message generique sans identifiant pour retrouver la cause.
- Les flows configure, ssm status, vpc status, liste des ressources et supprimer ne produisaient aucun log visible dans l'UI.

## 4. Solution

- Logger centralise JSON structure (une ligne JSON par log, parseable par jq ou tout log shipper).
- Niveaux de logs coherents : DEBUG pour les traces internes, INFO pour les evenements metier.
- Correlation via ContextVar : un UUID par requete HTTP, injecte dans chaque log et persiste en base.
- Endpoint GET /executions/{id}/logs avec parametre since pour le polling incremental.
- Hook useExecutionLogs et composant ExecutionLogList : affichage temps reel dans le chat, icone par niveau, auto-scroll.
- Logs d'execution pour tous les flows conversationnels (8 flows couverts).
- ErrorResponse expose le correlation_id pour relier un crash 500 cote client a sa cause dans les logs serveur.

## 5. Architecture modifiee

Frontend React -> FastAPI (middleware correlation_id) -> detection intention -> action cloud -> log_execution_event() -> ExecutionLog en base.

Frontend : useExecutionLogs poll GET /executions/{id}/logs toutes les 2s -> ExecutionLogList affiche les etapes en temps reel.

## 6. Demo nominale

Prompt:

```text
créer une instance nginx
```

Resultat attendu: le composant "Logs d'execution" apparait dans le chat et affiche les etapes started -> phase (generation Terraform) -> phase (apply) -> completed en temps reel.

## 7. Demo erreur

Prompt:

```text
supprimer
```

Puis donner un ID d'instance sans credentials provider associes.

Resultat attendu: les logs affichent started -> phase (tentative) -> phase (erreur 404 WARNING) -> failed. L'erreur est visible et comprehensible sans acces aux logs serveur.

## 8. Difficultes

- Le code backend est bake dans l'image Docker (pas de volume) : chaque modification Python necessite docker compose build.
- Les flows conversationnels n'utilisent pas le service d'execution asynchrone : log_execution_event() devait etre appele directement dans chaque handler.
- Propagation du correlation_id en contexte async : threading.local ne fonctionne pas, ContextVar etait obligatoire.

## 9. Limites

- Pas de streaming serveur (SSE/WebSocket) : delai de polling jusqu'a 2 secondes.
- Les logs d'execution restent en base indefiniment (pas de politique de retention).
- L'export vers un systeme centralise (Loki, Datadog) n'est pas implemente.
- La suppression retourne 404 si l'instance n'a pas d'entree provider avec credentials en base (probleme pre-existant, non introduit par ce challenge).

## 10. Perspectives

- Server-Sent Events (SSE) pour remplacer le polling.
- Centralisation vers Loki + Grafana ou Datadog.
- Politique de retention des logs (job periodique).
- Integration OpenTelemetry pour propager le correlation_id dans les sous-processus Terraform/Ansible.
