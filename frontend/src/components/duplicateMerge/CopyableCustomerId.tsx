import React from "react";
import { adminLabels } from "../../labels/adminLabels";
import { shortenCustomerId } from "./mergeSelectionState";

interface CopyableCustomerIdProps {
  value: string;
  className?: string;
}

export function CopyableCustomerId({ value, className }: CopyableCustomerIdProps) {
  const [copied, setCopied] = React.useState(false);

  const handleCopy = React.useCallback(async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  }, [value]);

  return (
    <span className={["duplicate-group-copyable-id", className].filter(Boolean).join(" ")}>
      <code title={value}>{shortenCustomerId(value)}</code>
      <button
        type="button"
        className="btn link duplicate-group-copy-id-btn"
        onClick={() => void handleCopy()}
        aria-label={adminLabels.dataOpCopyCustomerId}
      >
        {copied ? adminLabels.dataOpCopied : adminLabels.dataOpCopy}
      </button>
    </span>
  );
}
