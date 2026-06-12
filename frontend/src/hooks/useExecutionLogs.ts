import { useEffect, useRef, useState } from "react";
import axiosClient from "../api/axiosClient";

export interface ExecutionLog {
  id: number;
  event: string;
  level: "DEBUG" | "INFO" | "WARNING" | "ERROR";
  message: string | null;
  correlation_id: string | null;
  created_at: string;
}

interface ExecutionLogsState {
  logs: ExecutionLog[];
  done: boolean;
  status: string;
}

export function useExecutionLogs(
  executionId: number | null,
  enabled = true,
): ExecutionLogsState {
  const [state, setState] = useState<ExecutionLogsState>({
    logs: [],
    done: false,
    status: "idle",
  });

  const intervalRef = useRef<number | null>(null);
  const lastCreatedAtRef = useRef<string | null>(null);
  const errorsRef = useRef(0);

  useEffect(() => {
    if (!enabled || !executionId) {
      if (intervalRef.current) window.clearInterval(intervalRef.current);
      intervalRef.current = null;
      setState({ logs: [], done: false, status: "idle" });
      lastCreatedAtRef.current = null;
      return;
    }

    let cancelled = false;

    const fetchOnce = async () => {
      try {
        const params: Record<string, string> = {};
        if (lastCreatedAtRef.current) {
          params.since = lastCreatedAtRef.current;
        }
        const res = await axiosClient.get(
          `/executions/${executionId}/logs`,
          { params },
        );
        const data = res.data;
        errorsRef.current = 0;

        const newLogs: ExecutionLog[] = data.logs ?? [];
        if (newLogs.length > 0) {
          lastCreatedAtRef.current = newLogs[newLogs.length - 1].created_at;
        }

        if (!cancelled) {
          setState((prev) => ({
            logs: [...prev.logs, ...newLogs],
            done: !!data.done,
            status: data.status ?? "running",
          }));
        }

        if (data.done) {
          if (intervalRef.current) window.clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      } catch {
        errorsRef.current += 1;
        if (errorsRef.current >= 5) {
          if (intervalRef.current) window.clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      }
    };

    setState({ logs: [], done: false, status: "running" });
    lastCreatedAtRef.current = null;

    fetchOnce();
    intervalRef.current = window.setInterval(fetchOnce, 2000);

    return () => {
      cancelled = true;
      if (intervalRef.current) window.clearInterval(intervalRef.current);
      intervalRef.current = null;
    };
  }, [executionId, enabled]);

  return state;
}
