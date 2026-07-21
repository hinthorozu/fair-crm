import React from "react";
import { createPortal } from "react-dom";
import { useFloatingMenuPosition } from "../../hooks/useFloatingMenuPosition";
import { adminLabels } from "../../labels/adminLabels";
import type { MailOperationActionId, MailOperationRecord } from "../../types/mailOperations";
import {
  getMailOperationActions,
  mailOperationActionLabel,
} from "../../utils/mailOperations";
import { IconButton } from "../ui/IconButton";

export interface MailOperationActionHandlers {
  onDetail?: (record: MailOperationRecord) => void;
  onLogs?: (record: MailOperationRecord) => void;
  onCopy?: (record: MailOperationRecord) => void;
  onRetry?: (record: MailOperationRecord) => void;
  onErrorDetail?: (record: MailOperationRecord) => void;
  onCancel?: (record: MailOperationRecord) => void;
}

interface MailOperationActionsMenuProps extends MailOperationActionHandlers {
  record: MailOperationRecord;
  retryDisabled?: boolean;
}

const ACTION_HANDLERS: Record<
  MailOperationActionId,
  keyof MailOperationActionHandlers
> = {
  detail: "onDetail",
  logs: "onLogs",
  copy: "onCopy",
  retry: "onRetry",
  error_detail: "onErrorDetail",
  cancel: "onCancel",
};

export function MailOperationActionsMenu({
  record,
  onDetail,
  onLogs,
  onCopy,
  onRetry,
  onErrorDetail,
  onCancel,
  retryDisabled = false,
}: MailOperationActionsMenuProps) {
  const [open, setOpen] = React.useState(false);
  const anchorRef = React.useRef<HTMLDivElement>(null);
  const menuRef = React.useRef<HTMLDivElement>(null);
  const menuStyle = useFloatingMenuPosition(anchorRef, menuRef, open);

  const handlers: MailOperationActionHandlers = {
    onDetail,
    onLogs,
    onCopy,
    onRetry,
    onErrorDetail,
    onCancel,
  };

  const actions = getMailOperationActions(record.status).filter((action) => {
    const handlerKey = ACTION_HANDLERS[action];
    return Boolean(handlers[handlerKey]);
  });

  React.useEffect(() => {
    if (!open) return undefined;
    const onDocumentClick = (event: MouseEvent) => {
      const target = event.target as Node;
      if (anchorRef.current?.contains(target)) return;
      if (menuRef.current?.contains(target)) return;
      setOpen(false);
    };
    document.addEventListener("mousedown", onDocumentClick);
    return () => document.removeEventListener("mousedown", onDocumentClick);
  }, [open]);

  React.useEffect(() => {
    if (!open) return undefined;
    const onEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onEscape);
    return () => document.removeEventListener("keydown", onEscape);
  }, [open]);

  const runAction = (action: MailOperationActionId) => {
    if (action === "retry" && retryDisabled) return;
    const handlerKey = ACTION_HANDLERS[action];
    const handler = handlers[handlerKey];
    setOpen(false);
    handler?.(record);
  };

  const dropdown =
    open && typeof document !== "undefined"
      ? createPortal(
          <div
            ref={menuRef}
            className="mail-operation-actions-dropdown floating-dropdown-menu"
            role="menu"
            style={{
              top: menuStyle.top,
              left: menuStyle.left,
              minWidth: menuStyle.minWidth || undefined,
            }}
          >
            {actions.map((action) => (
              <button
                key={action}
                type="button"
                role="menuitem"
                className={`mail-template-actions-item ${action === "cancel" ? "danger" : ""}`.trim()}
                onClick={() => runAction(action)}
              >
                {mailOperationActionLabel(action)}
              </button>
            ))}
          </div>,
          document.body,
        )
      : null;

  return (
    <div className="mail-operation-actions-menu" ref={anchorRef}>
      <IconButton
        variant="kebab"
        label={adminLabels.mailOperationsActionsMenuLabel}
        icon={<span aria-hidden>⋮</span>}
        pressed={open}
        disabled={retryDisabled}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={(event) => {
          event.preventDefault();
          event.stopPropagation();
          setOpen((value) => !value);
        }}
      />
      {dropdown}
    </div>
  );
}
