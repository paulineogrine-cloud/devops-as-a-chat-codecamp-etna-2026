// useExecutionPolling.ts — version modifiée pour le Challenge 6
//
// CHANGEMENTS par rapport à l'original :
//   1. Ajout de `finalStatus` dans le state (null tant que pas terminé)
//   2. Quand status passe à "completed" ou "failed", finalStatus est mis à jour
//   3. Ajout de `resetFinalStatus()` pour réinitialiser entre deux exécutions

import { useEffect, useRef, useState } from "react";
import axiosClient from "../api/axiosClient";

export type ExecutionStatus = "pending" | "running" | "completed" | "failed";

export interface ExecutionSnapshot {
  execution_id: number;
  task_type: string;
  status: ExecutionStatus;
  progress?: number;
  progress_message?: string | null;
  updated_at?: string | null;
}

interface ExecutionPollingState {
  status: ExecutionStatus | "idle";
  progress: number;
  message: string;
  isPolling: boolean;
  // NOUVEAU — null tant qu'en cours, "completed" | "failed" à la fin
  finalStatus: "completed" | "failed" | null;
}

export function useExecutionPolling(
  executionId: number | null,
  enabled = true,
) {
  const [state, setState] = useState<ExecutionPollingState>({
    status: "idle",
    progress: 0,
    message: "",
    isPolling: false,
    finalStatus: null, // NOUVEAU
  });

  const intervalRef = useRef<number | null>(null);
  const errorsRef = useRef(0);

  // NOUVEAU — permet au parent de remettre finalStatus à null
  // (utile quand l'utilisateur ferme la bulle et relance une exécution)
  const resetFinalStatus = () => {
    setState((s) => ({ ...s, finalStatus: null }));
  };

  useEffect(() => {
    if (!enabled || !executionId) {
      if (intervalRef.current) window.clearInterval(intervalRef.current);
      intervalRef.current = null;
      setState((s) => ({ ...s, isPolling: false }));
      return;
    }

    let cancelled = false;

    const fetchOnce = async () => {
      try {
        const res = await axiosClient.get(`/executions/${executionId}`);
        const data = res.data;

        const status: ExecutionStatus = data.status;
        const progress = typeof data.progress === "number" ? data.progress : 0;
        const message = data.progress_message || "";

        errorsRef.current = 0;

        if (!cancelled) {
          setState((s) => ({
            ...s,
            status,
            progress,
            message,
            isPolling: true,
            // NOUVEAU — on mémorise le statut final dès qu'il arrive
            finalStatus:
              status === "completed" || status === "failed"
                ? status
                : s.finalStatus,
          }));
        }

        if (status === "completed" || status === "failed") {
          if (intervalRef.current) window.clearInterval(intervalRef.current);
          intervalRef.current = null;
          if (!cancelled) setState((s) => ({ ...s, isPolling: false }));
        }
      } catch (e) {
        errorsRef.current += 1;
        if (errorsRef.current >= 3) {
          if (intervalRef.current) window.clearInterval(intervalRef.current);
          intervalRef.current = null;
          if (!cancelled) setState((s) => ({ ...s, isPolling: false }));
        }
      }
    };

    setState({
      status: "running",
      progress: 0,
      message: "Démarrage…",
      isPolling: true,
      finalStatus: null, // reset à chaque nouvelle exécution
    });

    fetchOnce();
    intervalRef.current = window.setInterval(fetchOnce, 1500);

    return () => {
      cancelled = true;
      if (intervalRef.current) window.clearInterval(intervalRef.current);
      intervalRef.current = null;
    };
  }, [executionId, enabled]);

  return { ...state, resetFinalStatus };
}
