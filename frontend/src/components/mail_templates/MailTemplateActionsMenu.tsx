import React from "react";
import { createPortal } from "react-dom";
import { useFloatingMenuPosition } from "../../hooks/useFloatingMenuPosition";
import { adminLabels } from "../../labels/adminLabels";
import type { MailTemplate } from "../../types/mailTemplates";

export interface MailTemplateActionHandlers {
  onEdit?: (template: MailTemplate) => void;
  onPreview?: (template: MailTemplate) => void;
  onTestEmail?: (template: MailTemplate) => void;
  onSetDefault?: (template: MailTemplate) => void;
  onDelete?: (template: MailTemplate) => void;
}

interface MailTemplateActionsMenuProps extends MailTemplateActionHandlers {
  template: MailTemplate;
  canEdit: boolean;
  canPreview: boolean;
  canTestSend: boolean;
  canSetDefault: boolean;
  canDelete: boolean;
  busy?: boolean;
}

export function MailTemplateActionsMenu({
  template,
  canEdit,
  canPreview,
  canTestSend,
  canSetDefault,
  canDelete,
  busy = false,
  onEdit,
  onPreview,
  onTestEmail,
  onSetDefault,
  onDelete,
}: MailTemplateActionsMenuProps) {
  const [open, setOpen] = React.useState(false);
  const anchorRef = React.useRef<HTMLDivElement>(null);
  const menuRef = React.useRef<HTMLDivElement>(null);
  const menuStyle = useFloatingMenuPosition(anchorRef, menuRef, open);

  const hasAnyAction =
    (canEdit && onEdit) ||
    (canPreview && onPreview) ||
    (canTestSend && onTestEmail) ||
    (canSetDefault && onSetDefault) ||
    (canDelete && onDelete);

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
      if (event.key === "Escape") {
        setOpen(false);
      }
    };
    document.addEventListener("keydown", onEscape);
    return () => document.removeEventListener("keydown", onEscape);
  }, [open]);

  if (!hasAnyAction) {
    return <span className="text-muted">—</span>;
  }

  const runAction = (action?: (item: MailTemplate) => void) => {
    if (!action) return;
    setOpen(false);
    action(template);
  };

  const dropdown =
    open && typeof document !== "undefined"
      ? createPortal(
          <div
            ref={menuRef}
            className="mail-template-actions-dropdown floating-dropdown-menu"
            role="menu"
            style={{
              top: menuStyle.top,
              left: menuStyle.left,
              minWidth: menuStyle.minWidth || undefined,
            }}
          >
            {canEdit && onEdit ? (
              <button
                type="button"
                role="menuitem"
                className="mail-template-actions-item"
                onClick={() => runAction(onEdit)}
              >
                {adminLabels.mailTemplatesActionEdit}
              </button>
            ) : null}
            {canPreview && onPreview ? (
              <button
                type="button"
                role="menuitem"
                className="mail-template-actions-item"
                onClick={() => runAction(onPreview)}
              >
                {adminLabels.mailTemplatesActionPreview}
              </button>
            ) : null}
            {canTestSend && onTestEmail ? (
              <button
                type="button"
                role="menuitem"
                className="mail-template-actions-item"
                onClick={() => runAction(onTestEmail)}
              >
                {adminLabels.mailTemplatesActionTestEmail}
              </button>
            ) : null}
            {canSetDefault && onSetDefault ? (
              <button
                type="button"
                role="menuitem"
                className="mail-template-actions-item"
                onClick={() => runAction(onSetDefault)}
              >
                {adminLabels.mailTemplatesActionSetDefault}
              </button>
            ) : null}
            {canDelete && onDelete ? (
              <button
                type="button"
                role="menuitem"
                className="mail-template-actions-item danger"
                disabled={busy}
                onClick={() => runAction(onDelete)}
              >
                {adminLabels.mailTemplatesActionDelete}
              </button>
            ) : null}
          </div>,
          document.body,
        )
      : null;

  return (
    <div className="mail-template-actions-menu" ref={anchorRef}>
      <button
        type="button"
        className="btn btn-sm secondary"
        aria-haspopup="menu"
        aria-expanded={open}
        disabled={busy}
        onClick={(event) => {
          event.preventDefault();
          event.stopPropagation();
          setOpen((value) => !value);
        }}
      >
        {adminLabels.mailTemplatesActionsMenu}
      </button>
      {dropdown}
    </div>
  );
}
