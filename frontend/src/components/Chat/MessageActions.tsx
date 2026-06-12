import { Box, Button, alpha, useTheme } from "@mui/material";

interface ActionButton {
  label: string;
  value: string;
  color?: "primary" | "error" | "success" | "warning";
}

interface Props {
  state?: string;
  actions?: ActionButton[];
  onAction: (value: string) => void;
  disabled?: boolean;
}

const STATE_ACTIONS: Record<string, ActionButton[]> = {
  awaiting_create_confirmation: [
    { label: "Confirmer", value: "ok", color: "success" },
    { label: "Annuler", value: "annuler", color: "error" },
  ],
  awaiting_audit_confirmation: [
    { label: "Lancer l'audit", value: "lancer", color: "primary" },
    { label: "Annuler", value: "annuler", color: "error" },
  ],
  awaiting_monitoring_confirmation: [
    { label: "Lancer le monitoring", value: "lancer", color: "primary" },
    { label: "Annuler", value: "annuler", color: "error" },
  ],
  awaiting_instance_selection: [
    { label: "Toutes les instances", value: "toutes", color: "primary" },
    { label: "Annuler", value: "annuler", color: "error" },
  ],
  awaiting_audit_instance_selection: [
    { label: "Toutes les instances", value: "toutes", color: "primary" },
    { label: "Annuler", value: "annuler", color: "error" },
  ],
  awaiting_monitoring_instance_selection: [
    { label: "Toutes les instances", value: "toutes", color: "primary" },
    { label: "Annuler", value: "annuler", color: "error" },
  ],
  awaiting_ssm_fix_confirm: [
    { label: "Oui, configurer SSM", value: "oui", color: "success" },
    { label: "Non", value: "non", color: "error" },
  ],
};

export default function MessageActions({ state, actions, onAction, disabled }: Props) {
  const theme = useTheme();

  const buttons: ActionButton[] = actions ?? (state ? (STATE_ACTIONS[state] ?? []) : []);

  if (buttons.length === 0) return null;

  return (
    <Box
      sx={{
        display: "flex",
        gap: 1,
        flexWrap: "wrap",
        ml: 6,
        mt: 1,
        mb: 0.5,
      }}
    >
      {buttons.map((btn) => (
        <Button
          key={btn.value}
          size="small"
          variant="outlined"
          color={btn.color ?? "primary"}
          disabled={disabled}
          onClick={() => onAction(btn.value)}
          sx={{
            borderRadius: 2,
            textTransform: "none",
            fontSize: "0.8rem",
            px: 1.5,
            py: 0.5,
            bgcolor: alpha(
              theme.palette[btn.color ?? "primary"].main,
              0.06,
            ),
            "&:hover": {
              bgcolor: alpha(
                theme.palette[btn.color ?? "primary"].main,
                0.14,
              ),
            },
          }}
        >
          {btn.label}
        </Button>
      ))}
    </Box>
  );
}
