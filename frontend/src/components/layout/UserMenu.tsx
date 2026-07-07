import React from "react";
import { createPortal } from "react-dom";
import { useAuth } from "../../auth/AuthContext";
import { useFloatingMenuPosition } from "../../hooks/useFloatingMenuPosition";
import { authLabels } from "../../labels/authLabels";

interface UserMenuProps {
  onLogout: () => void | Promise<void>;
}

function displayEmail(email: string | undefined): string {
  const trimmed = email?.trim();
  return trimmed || "—";
}

export function UserMenu({ onLogout }: UserMenuProps) {
  const { session } = useAuth();
  const [open, setOpen] = React.useState(false);
  const [submitting, setSubmitting] = React.useState(false);
  const anchorRef = React.useRef<HTMLDivElement>(null);
  const menuRef = React.useRef<HTMLDivElement>(null);
  const menuStyle = useFloatingMenuPosition(anchorRef, menuRef, open);

  const email = displayEmail(session?.email);
  const organizationId = session?.organizationId ?? "";

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

  const handleLogout = async () => {
    if (submitting) return;
    setSubmitting(true);
    setOpen(false);
    try {
      await onLogout();
    } finally {
      setSubmitting(false);
    }
  };

  const dropdown =
    open && typeof document !== "undefined"
      ? createPortal(
          <div
            ref={menuRef}
            className="user-menu-dropdown floating-dropdown-menu"
            role="menu"
            style={{
              top: menuStyle.top,
              left: menuStyle.left,
              minWidth: menuStyle.minWidth || undefined,
            }}
          >
            <div className="user-menu-meta" role="presentation">
              <span className="user-menu-meta-label">{email}</span>
              {organizationId ? (
                <span className="user-menu-meta-sub">
                  {authLabels.organization}: {organizationId.slice(0, 8)}…
                </span>
              ) : null}
            </div>
            <button
              type="button"
              role="menuitem"
              className="mail-template-actions-item danger"
              disabled={submitting}
              onClick={() => void handleLogout()}
            >
              {submitting ? authLabels.loggingOut : authLabels.logout}
            </button>
          </div>,
          document.body,
        )
      : null;

  return (
    <div className="user-menu" ref={anchorRef}>
      <button
        type="button"
        className="user-menu-trigger"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={authLabels.userMenuLabel}
        disabled={submitting}
        onClick={() => setOpen((value) => !value)}
      >
        <span className="user-menu-trigger-label">{email}</span>
        <span className="user-menu-trigger-caret" aria-hidden>
          ▾
        </span>
      </button>
      {dropdown}
    </div>
  );
}
