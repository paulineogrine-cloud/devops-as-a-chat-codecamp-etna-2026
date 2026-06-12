import React, { useEffect, useRef, useState } from "react";
import {
  Box,
  Chip,
  Collapse,
  IconButton,
  Typography,
} from "@mui/material";
import {
  Circle as CircleIcon,
  ExpandLess as ExpandLessIcon,
} from "@mui/icons-material";
import type { ExecutionLog } from "../../hooks/useExecutionLogs";

interface Props {
  logs: ExecutionLog[];
  done?: boolean;
}

function levelColor(level: string): string {
  switch (level) {
    case "ERROR":
      return "#f44336";
    case "WARNING":
      return "#ff9800";
    case "DEBUG":
      return "#9e9e9e";
    default:
      return "#2196f3";
  }
}

function levelLabel(level: string): string {
  switch (level) {
    case "ERROR":
      return "ERR";
    case "WARNING":
      return "WARN";
    case "DEBUG":
      return "DBG";
    default:
      return "INFO";
  }
}

const ExecutionLogList: React.FC<Props> = ({ logs, done }) => {
  const [expanded, setExpanded] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (expanded && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs, expanded]);

  if (logs.length === 0 && done) return null;

  return (
    <Box sx={{ mt: 1, border: "1px solid", borderColor: "divider", borderRadius: 1, overflow: "hidden" }}>
      <Box
        display="flex"
        alignItems="center"
        justifyContent="space-between"
        sx={{ px: 1.5, py: 0.5, bgcolor: "rgba(0,0,0,0.04)", cursor: "pointer" }}
        onClick={() => setExpanded((v) => !v)}
      >
        <Box display="flex" alignItems="center" gap={1}>
          <Typography variant="caption" fontWeight={600} sx={{ fontFamily: "monospace" }}>
            Logs d'exécution
          </Typography>
          <Chip label={`${logs.length}`} size="small" variant="outlined" color="info" sx={{ height: 18, fontSize: "0.65rem" }} />
          {!done && (
            <CircleIcon sx={{ fontSize: 8, color: "#4caf50", animation: "pulse 1.5s infinite" }} />
          )}
        </Box>
        <IconButton
          size="small"
          sx={{ transform: expanded ? "rotate(0deg)" : "rotate(180deg)", transition: "transform 0.2s" }}
        >
          <ExpandLessIcon fontSize="small" />
        </IconButton>
      </Box>

      <Collapse in={expanded}>
        <Box
          sx={{
            maxHeight: 280,
            overflowY: "auto",
            bgcolor: "#0d1117",
            p: 1,
          }}
        >
          {logs.map((log) => (
            <Box key={log.id} display="flex" alignItems="flex-start" gap={1} sx={{ mb: 0.3 }}>
              <Typography
                variant="caption"
                sx={{
                  fontFamily: "monospace",
                  color: levelColor(log.level),
                  minWidth: 36,
                  flexShrink: 0,
                  fontWeight: 700,
                }}
              >
                {levelLabel(log.level)}
              </Typography>
              <Typography
                variant="caption"
                sx={{
                  fontFamily: "monospace",
                  color: "#c9d1d9",
                  wordBreak: "break-all",
                  flex: 1,
                }}
              >
                {log.message ?? log.event}
              </Typography>
              <Typography
                variant="caption"
                sx={{ fontFamily: "monospace", color: "#484f58", flexShrink: 0, fontSize: "0.6rem" }}
              >
                {new Date(log.created_at).toLocaleTimeString("fr-FR")}
              </Typography>
            </Box>
          ))}
          <div ref={bottomRef} />
        </Box>
      </Collapse>
    </Box>
  );
};

export default ExecutionLogList;
