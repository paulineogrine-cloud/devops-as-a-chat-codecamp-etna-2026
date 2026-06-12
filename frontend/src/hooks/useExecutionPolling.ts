import { useEffect, useRef, useState } from "react";
import axiosClient from "../api/axiosClient";
import { useExecutionLogs } from "./useExecutionLogs";
export type { ExecutionLog } from "./useExecutionLogs";

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
  executionLogs: ReturnType<typeof useExecutionLogs>["logs"];
  logsDone: boolean;
}

export function useExecutionPolling(
  executionId: number | null,
  enabled = true,
) {
  const { logs: executionLogs, done: logsDone } = useExecutionLogs(executionId, enabled);

  const [state, setState] = useState<ExecutionPollingState>({
    status: "idle",
    progress: 0,
    message: "",
    isPolling: false,
    executionLogs: [],
    logsDone: false,
  });

  const intervalRef = useRef<number | null>(null);
  const errorsRef = useRef(0);

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
          setState((prev) => ({
            ...prev,
            status,
            progress,
            message,
            isPolling: true,
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

    // reset state à chaque nouvel id
    setState({
      status: "running",
      progress: 0,
      message: "Démarrage…",
      isPolling: true,
      executionLogs: [],
      logsDone: false,
    });

    fetchOnce();
    intervalRef.current = window.setInterval(fetchOnce, 1500);

    return () => {
      cancelled = true;
      if (intervalRef.current) window.clearInterval(intervalRef.current);
      intervalRef.current = null;
    };
  }, [executionId, enabled]);

  // Synchroniser les logs en dehors du useEffect pour éviter un cycle
  const stateWithLogs = { ...state, executionLogs, logsDone };

  return stateWithLogs;
}
