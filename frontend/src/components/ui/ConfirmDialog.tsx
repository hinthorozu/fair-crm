import React from "react";
import { labels } from "../../labels";
import { uiLabels } from "../../labels/uiLabels";

/** Confirmation overlay — ADR-028: closes only via explicit action buttons. */
interface ConfirmDialogProps {
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "danger" | "default";
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  className?: string;
}

export function ConfirmDialog({
  title,
  message,
  confirmLabel = uiLabels.confirm,
  cancelLabel = labels.cancel,
  variant = "default",
  loading = false,
  onConfirm,
  onCancel,
  className = "",
}: ConfirmDialogProps) {
  const confirmRef = React.useRef<HTMLButtonElement>(null);

  React.useEffect(() => {
    confirmRef.current?.focus();
  }, []);

  return (
    <div className={`modal-backdrop ${className}`.trim()} role="presentation">
      <div
        className="modal modal-sm"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
        aria-describedby="confirm-message"
      >
        <header className="modal-header">
          <h2 id="confirm-title">{title}</h2>
        </header>
        <div className="modal-body">
          <p id="confirm-message" className="confirm-message">
            {message}
          </p>
          <div className="form-actions">
            <button type="button" className="btn secondary" onClick={onCancel} disabled={loading}>
              {cancelLabel}
            </button>
            <button
              ref={confirmRef}
              type="button"
              className={variant === "danger" ? "btn danger" : "btn primary"}
              onClick={onConfirm}
              disabled={loading}
            >
              {loading ? labels.loading : confirmLabel}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
