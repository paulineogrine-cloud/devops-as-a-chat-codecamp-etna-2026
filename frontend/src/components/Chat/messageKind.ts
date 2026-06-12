import {
  InfoOutlined,
  BuildOutlined,
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
    color: "#2196f3",
    Icon: InfoOutlined,
    label: "Information",
  },
  proposal: {
    color: "#ff9800",
    Icon: BuildOutlined,
    label: "Action proposée",
  },
  executed: {
    color: "#4caf50",
    Icon: CheckCircleOutlined,
    label: "Action exécutée",
  },
  error: {
    color: "#f44336",
    Icon: ErrorOutlined,
    label: "Erreur",
  },
};

interface MessageLike {
  extra?: { kind?: string; state?: string } | any;
  text?: string;
}

export function resolveKind(message: MessageLike): MessageKind | null {
  const kind = message.extra?.kind;
  if (kind && kind in KIND_META) return kind as MessageKind;

  const state = message.extra?.state;
  if (state === "error" || state === "failed") return "error";
  if (state === "completed" || state === "executed") return "executed";
  if (state === "awaiting_confirmation" || state === "proposal") return "proposal";

  return null;
}
