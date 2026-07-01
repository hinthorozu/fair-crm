import React from "react";
import { labels } from "../../labels";
import { uiLabels } from "../../labels/uiLabels";

interface ConfirmDialogProps {
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "danger" | "default";
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
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
}: ConfirmDialogProps) {
  const confirmRef = React.useRef<HTMLButtonElement>(null);

  React.useEffect(() => {
    confirmRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCancel();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onCancel]);

  return (
    <div className="modal-backdrop" onClick={onCancel} role="presentation">
      <div
        className="modal modal-sm"
        onClick={(e) => e.stopPropagation()}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
        aria-describedby="confirm-message"
      >
        <header className="modal-header">
          <h2 id="confirm-title">{title}</h2>
        </header>
        <div className="modal-body">
          <p id="confirm-message" className="confirm-message">{message}</p>
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
