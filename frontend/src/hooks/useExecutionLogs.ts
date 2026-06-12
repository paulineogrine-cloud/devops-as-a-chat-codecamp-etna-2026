import { useEffect, useRef, useState, useCallback } from "react";
import axiosClient from "../api/axiosClient";

export interface ExecutionLogEntry {
  id: number;
  event: string;
  level: "DEBUG" | "INFO" | "WARNING" | "ERROR";
  message: string | null;
  correlation_id: string | null;
  created_at: string;
}

interface State {
  logs: ExecutionLogEntry[];
  isPolling: boolean;
  error: string | null;
}

/**
 * Polling sur GET /executions/{id}/logs
 *
 * - Démarre le polling dès que executionId est fourni et enabled est true.
 * - Envoie `since` = created_at du dernier log connu pour n'obtenir que les nouveaux.
 * - Arrête automatiquement dès que done = true (exécution terminée).
 */
export function useExecutionLogs(
  executionId: number | null,
  {
    enabled = true,
    done = false,
    intervalMs = 2000,
  }: { enabled?: boolean; done?: boolean; intervalMs?: number } = {},
) {
  const [state, setState] = useState<State>({
    logs: [],
    isPolling: false,
    error: null,
  });

  // Garder le dernier created_at connu pour le paramètre `since`
  const lastTimestampRef = useRef<string | null>(null);
  const timerRef = useRef<number | null>(null);
  const cancelledRef = useRef(false);

  const clearTimer = () => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  };

  const fetchOnce = useCallback(async () => {
    if (!executionId || cancelledRef.current) return;

    try {
      const params: Record<string, string | number> = { limit: 100 };
      if (lastTimestampRef.current) {
        params.since = lastTimestampRef.current;
      }

      const res = await axiosClient.get(`/executions/${executionId}/logs`, { params });
      const entries: ExecutionLogEntry[] = res.data.logs ?? [];

      if (entries.length > 0 && !cancelledRef.current) {
        lastTimestampRef.current = entries[entries.length - 1].created_at;
        setState((prev) => ({
          ...prev,
          logs: [...prev.logs, ...entries],
          isPolling: true,
          error: null,
        }));
      }
    } catch (e: any) {
      if (!cancelledRef.current) {
        setState((prev) => ({ ...prev, error: e?.message ?? "Erreur réseau" }));
      }
    }

    // Replanifier si la tâche n'est pas terminée
    if (!done && !cancelledRef.current) {
      timerRef.current = window.setTimeout(fetchOnce, intervalMs);
    } else if (!cancelledRef.current) {
      setState((prev) => ({ ...prev, isPolling: false }));
    }
  }, [executionId, done, intervalMs]);

  useEffect(() => {
    if (!enabled || !executionId) {
      clearTimer();
      setState({ logs: [], isPolling: false, error: null });
      lastTimestampRef.current = null;
      return;
    }

    cancelledRef.current = false;
    setState((prev) => ({ ...prev, isPolling: true }));
    fetchOnce();

    return () => {
      cancelledRef.current = true;
      clearTimer();
    };
  }, [executionId, enabled, fetchOnce]);

  // Quand done passe à true, arrêter le polling après un dernier fetch
  useEffect(() => {
    if (done && state.isPolling) {
      clearTimer();
      // Un dernier fetch pour capturer les logs finaux
      fetchOnce();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [done]);

  return state;
}
