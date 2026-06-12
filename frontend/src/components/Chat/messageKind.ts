import {
  InfoOutlined,
  PendingOutlined,
  CheckCircleOutlined,
  ErrorOutlined,
} from "@mui/icons-material";

export type MessageKind = "info" | "proposal" | "executed" | "error";

interface KindMeta {
  color: string;
  Icon: React.ElementType;
  label: string;
}

export const KIND_META: Record<MessageKind, KindMeta> = {
  info: {
    color: "#6366f1",
    Icon: InfoOutlined,
    label: "Information",
  },
  proposal: {
    color: "#f59e0b",
    Icon: PendingOutlined,
    label: "Action proposée",
  },
  executed: {
    color: "#10b981",
    Icon: CheckCircleOutlined,
    label: "Action exécutée",
  },
  error: {
    color: "#ef4444",
    Icon: ErrorOutlined,
    label: "Erreur",
  },
};

const PROPOSAL_STATES = new Set([
  "awaiting_create_confirmation",
  "awaiting_audit_confirmation",
  "awaiting_monitoring_confirmation",
  "awaiting_instance_selection",
  "awaiting_audit_instance_selection",
  "awaiting_monitoring_instance_selection",
  "awaiting_ssm_fix_confirm",
  "awaiting_create_params",
]);

const ERROR_PATTERNS = [
  /erreur/i, /error/i, /échec/i, /echoue/i, /failed/i, /introuvable/i,
];

const SUCCESS_PATTERNS = [
  /termin[eé]/i, /cr[eé][eé]/i, /succ[eè]s/i, /complet/i,
  /configuration termin/i, /déploiement/i,
];

interface Message {
  sender?: string;
  kind?: string;
  text?: string;
  extra?: { kind?: string; state?: string; error?: unknown } | any;
}

export function resolveKind(message: Message): MessageKind | null {
  // Explicit kind wins
  const explicit = (message.kind ?? message.extra?.kind ?? "") as string;
  if (explicit && explicit in KIND_META) return explicit as MessageKind;

  const state: string = message.extra?.state ?? "";
  const text: string = message.text ?? "";

  // Error: explicit error field or error text patterns
  if (message.extra?.error || ERROR_PATTERNS.some((re) => re.test(text))) {
    return "error";
  }

  // Proposal: confirmation/selection states
  if (PROPOSAL_STATES.has(state)) return "proposal";

  // Executed: success text patterns
  if (SUCCESS_PATTERNS.some((re) => re.test(text))) return "executed";

  // Default: informational (return null to show no badge for generic messages)
  return null;
}
