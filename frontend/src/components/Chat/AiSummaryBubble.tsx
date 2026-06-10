// src/components/Chat/AiSummaryBubble.tsx
//
// Bulle IA qui s'affiche quand une exécution se termine.
// Elle récupère l'ai_summary depuis GET /executions/{id}
// et l'affiche avec un statut (succès / erreur) + bouton fermer.

import React, { useEffect, useState } from "react";
import {
  Box,
  Paper,
  Typography,
  IconButton,
  Collapse,
  Chip,
  Divider,
  CircularProgress,
  alpha,
  useTheme,
} from "@mui/material";
import {
  Close as CloseIcon,
  AutoAwesome as AutoAwesomeIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
} from "@mui/icons-material";
import axiosClient from "../../api/axiosClient";

// ---------- Types ----------

interface AiSummaryData {
  status: "success" | "error" | "warning";
  summary: string;
  fix: string | null;
  // Champs optionnels si le backend renvoie des étapes détaillées
  failed_steps?: string[];
  successful_steps?: string[];
}

interface AiSummaryBubbleProps {
  /** L'ID de l'exécution à analyser. null = caché */
  executionId: number | null;
  /** Statut final de l'exécution (completed | failed) */
  executionStatus: "completed" | "failed" | null;
  /** Callback quand l'utilisateur ferme la bulle */
  onClose: () => void;
}

// ---------- Icône selon le statut IA ----------

function StatusIcon({ status }: { status: AiSummaryData["status"] }) {
  if (status === "success")
    return <CheckCircleIcon sx={{ color: "#10b981", fontSize: 20 }} />;
  if (status === "error")
    return <ErrorIcon sx={{ color: "#ef4444", fontSize: 20 }} />;
  return <WarningIcon sx={{ color: "#f59e0b", fontSize: 20 }} />;
}

// ---------- Couleurs selon le statut IA ----------

function statusColors(status: AiSummaryData["status"]) {
  if (status === "success")
    return { border: "#10b981", bg: "rgba(16,185,129,0.06)", chip: "#10b981" };
  if (status === "error")
    return { border: "#ef4444", bg: "rgba(239,68,68,0.06)", chip: "#ef4444" };
  return { border: "#f59e0b", bg: "rgba(245,158,11,0.06)", chip: "#f59e0b" };
}

// ---------- Composant principal ----------

export default function AiSummaryBubble({
  executionId,
  executionStatus,
  onClose,
}: AiSummaryBubbleProps) {
  const theme = useTheme();

  const [summary, setSummary] = useState<AiSummaryData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(true); // La bulle est ouverte par défaut
  const [stepsExpanded, setStepsExpanded] = useState(false);

  // Quand l'exécution se termine, on appelle l'API pour récupérer l'ai_summary
  useEffect(() => {
    if (
      !executionId ||
      (executionStatus !== "completed" && executionStatus !== "failed")
    ) {
      return;
    }

    setLoading(true);
    setError(null);
    setSummary(null);

    axiosClient
      .get(`/executions/${executionId}?analyze=true`)
      .then((res) => {
        const data = res.data;
        if (data.ai_summary) {
          setSummary(data.ai_summary);
        } else {
          // Le backend n'a pas encore l'IA — afficher un message générique
          setSummary({
            status: executionStatus === "completed" ? "success" : "error",
            summary:
              executionStatus === "completed"
                ? "Exécution terminée avec succès."
                : "L'exécution a échoué. Consultez les logs pour les détails.",
            fix: null,
          });
        }
      })
      .catch(() => {
        setError("Impossible de récupérer l'analyse IA.");
      })
      .finally(() => setLoading(false));
  }, [executionId, executionStatus]);

  // Ne rien afficher si pas d'exécution terminée
  if (!executionId || (executionStatus !== "completed" && executionStatus !== "failed")) {
    return null;
  }

  const colors = summary ? statusColors(summary.status) : null;

  return (
    <Collapse in={open} timeout={300}>
      <Paper
        elevation={0}
        sx={{
          mb: 2,
          border: `1px solid ${colors ? colors.border : alpha(theme.palette.primary.main, 0.3)}`,
          borderRadius: 3,
          bgcolor: colors ? colors.bg : alpha(theme.palette.primary.main, 0.04),
          overflow: "hidden",
          transition: "all 0.3s ease",
        }}
      >
        {/* En-tête de la bulle */}
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 1,
            px: 2,
            py: 1.5,
            borderBottom: loading || summary ? `1px solid ${alpha("#000", 0.06)}` : "none",
          }}
        >
          <AutoAwesomeIcon
            sx={{
              fontSize: 18,
              color: theme.palette.primary.main,
              animation: loading ? "spin 1.5s linear infinite" : "none",
              "@keyframes spin": {
                "0%": { transform: "rotate(0deg)" },
                "100%": { transform: "rotate(360deg)" },
              },
            }}
          />
          <Typography variant="caption" fontWeight={600} sx={{ flex: 1, color: "text.secondary", letterSpacing: 0.5, textTransform: "uppercase" }}>
            Analyse IA
          </Typography>

          {summary && (
            <Chip
              size="small"
              label={
                summary.status === "success"
                  ? "Succès"
                  : summary.status === "error"
                    ? "Erreur détectée"
                    : "Avertissement"
              }
              icon={<StatusIcon status={summary.status} />}
              sx={{
                bgcolor: alpha(colors!.chip, 0.1),
                color: colors!.chip,
                borderColor: alpha(colors!.chip, 0.3),
                border: "1px solid",
                fontWeight: 600,
                fontSize: "0.7rem",
                "& .MuiChip-icon": { fontSize: 14 },
              }}
            />
          )}

          {/* Bouton fermer */}
          <IconButton
            size="small"
            onClick={() => {
              setOpen(false);
              setTimeout(onClose, 300); // laisser l'animation se terminer
            }}
            sx={{ color: "text.secondary", ml: 0.5 }}
            aria-label="Fermer l'analyse IA"
          >
            <CloseIcon fontSize="small" />
          </IconButton>
        </Box>

        {/* Corps */}
        <Box sx={{ px: 2, py: 1.5 }}>
          {/* Chargement */}
          {loading && (
            <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
              <CircularProgress size={16} thickness={5} />
              <Typography variant="body2" color="text.secondary">
                Analyse des logs en cours…
              </Typography>
            </Box>
          )}

          {/* Erreur réseau */}
          {error && (
            <Typography variant="body2" color="error">
              {error}
            </Typography>
          )}

          {/* Résumé IA */}
          {summary && !loading && (
            <>
              {/* Résumé principal */}
              <Typography variant="body2" sx={{ lineHeight: 1.7, color: "text.primary" }}>
                {summary.summary}
              </Typography>

              {/* Suggestion de correction si erreur */}
              {summary.fix && (
                <>
                  <Divider sx={{ my: 1.5 }} />
                  <Box
                    sx={{
                      bgcolor: alpha("#3b82f6", 0.06),
                      border: "1px solid",
                      borderColor: alpha("#3b82f6", 0.2),
                      borderRadius: 2,
                      px: 1.5,
                      py: 1,
                    }}
                  >
                    <Typography
                      variant="caption"
                      fontWeight={600}
                      sx={{ color: "#3b82f6", display: "block", mb: 0.5, textTransform: "uppercase", letterSpacing: 0.5 }}
                    >
                      💡 Action recommandée
                    </Typography>
                    <Typography variant="body2" sx={{ lineHeight: 1.6, color: "text.primary" }}>
                      {summary.fix}
                    </Typography>
                  </Box>
                </>
              )}

              {/* Étapes ayant échoué (si le backend les fournit) */}
              {summary.failed_steps && summary.failed_steps.length > 0 && (
                <>
                  <Divider sx={{ my: 1.5 }} />
                  <Box
                    sx={{ cursor: "pointer" }}
                    onClick={() => setStepsExpanded((v) => !v)}
                  >
                    <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                      <Typography
                        variant="caption"
                        fontWeight={600}
                        sx={{ color: "#ef4444", textTransform: "uppercase", letterSpacing: 0.5 }}
                      >
                        Étapes en échec ({summary.failed_steps.length})
                      </Typography>
                      {stepsExpanded ? (
                        <ExpandLessIcon sx={{ fontSize: 16, color: "#ef4444" }} />
                      ) : (
                        <ExpandMoreIcon sx={{ fontSize: 16, color: "#ef4444" }} />
                      )}
                    </Box>
                  </Box>

                  <Collapse in={stepsExpanded}>
                    <Box sx={{ mt: 1, display: "flex", flexDirection: "column", gap: 0.5 }}>
                      {summary.failed_steps.map((step, i) => (
                        <Box
                          key={i}
                          sx={{
                            display: "flex",
                            alignItems: "flex-start",
                            gap: 1,
                            bgcolor: alpha("#ef4444", 0.05),
                            borderRadius: 1,
                            px: 1,
                            py: 0.5,
                          }}
                        >
                          <ErrorIcon sx={{ fontSize: 14, color: "#ef4444", mt: 0.3, flexShrink: 0 }} />
                          <Typography variant="caption" sx={{ color: "text.primary", lineHeight: 1.5 }}>
                            {step}
                          </Typography>
                        </Box>
                      ))}
                    </Box>
                  </Collapse>
                </>
              )}
            </>
          )}
        </Box>
      </Paper>
    </Collapse>
  );
}
