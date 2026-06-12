import React from "react";
import {
  Box,
  Chip,
  Collapse,
  IconButton,
  List,
  ListItem,
  Typography,
} from "@mui/material";
import {
  ExpandLess as ExpandLessIcon,
  BugReport as DebugIcon,
  Info as InfoIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
} from "@mui/icons-material";
import type { ExecutionLogEntry } from "../../hooks/useExecutionLogs";

interface Props {
  logs: ExecutionLogEntry[];
  isPolling?: boolean;
  maxVisible?: number;
}

const LEVEL_CONFIG = {
  DEBUG:   { color: "#9e9e9e", icon: <DebugIcon   sx={{ fontSize: 14 }} /> },
  INFO:    { color: "#2196f3", icon: <InfoIcon     sx={{ fontSize: 14 }} /> },
  WARNING: { color: "#ff9800", icon: <WarningIcon  sx={{ fontSize: 14 }} /> },
  ERROR:   { color: "#f44336", icon: <ErrorIcon    sx={{ fontSize: 14 }} /> },
} as const;

function levelConfig(level: string) {
  return LEVEL_CONFIG[level as keyof typeof LEVEL_CONFIG] ?? LEVEL_CONFIG.INFO;
}

const ExecutionLogList: React.FC<Props> = ({
  logs,
  isPolling = false,
  maxVisible = 50,
}) => {
  const [open, setOpen] = React.useState(true);
  const listRef = React.useRef<HTMLUListElement>(null);

  // Auto-scroll vers le bas à chaque nouveau log
  React.useEffect(() => {
    if (open && listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [logs.length, open]);

  const visible = logs.slice(-maxVisible);

  return (
    <Box>
      {/* En-tête */}
      <Box display="flex" alignItems="center" justifyContent="space-between" mb={0.5}>
        <Box display="flex" alignItems="center" gap={1}>
          <Typography variant="subtitle2" fontWeight={600}>
            Logs d'exécution
          </Typography>
          <Chip
            label={isPolling ? `${logs.length} (en cours…)` : `${logs.length}`}
            size="small"
            variant="outlined"
            color={isPolling ? "primary" : "default"}
          />
        </Box>
        <IconButton
          size="small"
          onClick={() => setOpen((v) => !v)}
          sx={{
            transform: open ? "rotate(0deg)" : "rotate(180deg)",
            transition: "transform 0.2s",
          }}
        >
          <ExpandLessIcon />
        </IconButton>
      </Box>

      <Collapse in={open}>
        <Box
          sx={{
            border: "1px solid",
            borderColor: "divider",
            borderRadius: 2,
            overflow: "hidden",
          }}
        >
          {visible.length === 0 ? (
            <Box py={3} textAlign="center">
              <Typography variant="body2" color="text.secondary">
                {isPolling ? "En attente des premiers logs…" : "Aucun log disponible."}
              </Typography>
            </Box>
          ) : (
            <List
              ref={listRef}
              dense
              disablePadding
              sx={{
                maxHeight: 280,
                overflowY: "auto",
                fontFamily: "monospace",
                fontSize: "0.78rem",
              }}
            >
              {visible.map((log, i) => {
                const cfg = levelConfig(log.level);
                return (
                  <ListItem
                    key={log.id ?? i}
                    divider
                    sx={{
                      py: 0.5,
                      px: 1.5,
                      gap: 1,
                      alignItems: "flex-start",
                      "&:nth-of-type(odd)": { bgcolor: "rgba(0,0,0,0.02)" },
                    }}
                  >
                    {/* Icône niveau */}
                    <Box
                      sx={{ color: cfg.color, mt: "2px", flexShrink: 0 }}
                      title={log.level}
                    >
                      {cfg.icon}
                    </Box>

                    {/* Corps du log */}
                    <Box flex={1} minWidth={0}>
                      <Typography
                        variant="body2"
                        sx={{
                          wordBreak: "break-word",
                          fontFamily: "monospace",
                          fontSize: "0.78rem",
                          color: cfg.color,
                        }}
                      >
                        {log.message ?? "(vide)"}
                      </Typography>
                      <Box display="flex" gap={0.5} mt={0.25} flexWrap="wrap">
                        <Typography
                          variant="caption"
                          color="text.disabled"
                          sx={{ fontFamily: "monospace" }}
                        >
                          {new Date(log.created_at).toLocaleTimeString("fr-FR")}
                        </Typography>
                        <Chip
                          label={log.event}
                          size="small"
                          variant="outlined"
                          sx={{ height: 16, fontSize: "0.65rem" }}
                        />
                      </Box>
                    </Box>
                  </ListItem>
                );
              })}
            </List>
          )}
        </Box>
      </Collapse>
    </Box>
  );
};

export default ExecutionLogList;
