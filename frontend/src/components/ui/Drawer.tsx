import React from "react";
import { labels } from "../../labels";

interface DrawerProps {
  title: string;
  subtitle?: string;
  onClose: () => void;
  children: React.ReactNode;
}

export function Drawer({ title, subtitle, onClose, children }: DrawerProps) {
  const closeRef = React.useRef<HTMLButtonElement>(null);

  React.useEffect(() => {
    closeRef.current?.focus();
  }, []);

  React.useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return (
    <>
      <div className="drawer-backdrop" role="presentation" onClick={onClose} />
      <aside className="drawer-panel" role="dialog" aria-modal="true" aria-labelledby="drawer-title">
        <header className="drawer-header">
          <div className="drawer-header-text">
            <h2 id="drawer-title">{title}</h2>
            {subtitle ? <p className="drawer-subtitle text-muted">{subtitle}</p> : null}
          </div>
          <button
            ref={closeRef}
            type="button"
            className="btn icon"
            onClick={onClose}
            aria-label={labels.cancel}
          >
            ×
          </button>
        </header>
        <div className="drawer-body">{children}</div>
      </aside>
    </>
  );
}
