import React from "react";
import { Box, Button } from "@mui/material";

interface Props {
  state?: string;
  actions?: string[];
  onAction?: (value: string) => void;
  disabled?: boolean;
}

const MessageActions: React.FC<Props> = ({ actions, onAction, disabled }) => {
  if (!actions || actions.length === 0) return null;

  return (
    <Box display="flex" gap={1} flexWrap="wrap" sx={{ mt: 1 }}>
      {actions.map((action) => (
        <Button
          key={action}
          size="small"
          variant="outlined"
          disabled={disabled}
          onClick={() => onAction?.(action)}
        >
          {action}
        </Button>
      ))}
    </Box>
  );
};

export default MessageActions;
