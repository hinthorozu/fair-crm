import React from "react";
import { labels } from "../../labels";

/** Overlay dialog — focus/escape/backdrop behavior follows shared modal focus pattern (see .cursor/rules/shared-modal-focus.mdc). */
interface ModalProps {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
  size?: "default" | "lg";
}

const FOCUSABLE_SELECTOR =
  'textarea, input:not([type="hidden"]), select, button:not([disabled]), [href], [tabindex]:not([tabindex="-1"])';

function focusInitialElement(body: HTMLElement | null, closeButton: HTMLButtonElement | null) {
  const firstFocusable = body?.querySelector<HTMLElement>(FOCUSABLE_SELECTOR);
  if (firstFocusable) {
    firstFocusable.focus();
    return;
  }
  closeButton?.focus();
}

export function Modal({ title, onClose, children, size = "default" }: ModalProps) {
  const closeRef = React.useRef<HTMLButtonElement>(null);
  const bodyRef = React.useRef<HTMLDivElement>(null);
  const onCloseRef = React.useRef(onClose);
  onCloseRef.current = onClose;

  React.useEffect(() => {
    focusInitialElement(bodyRef.current, closeRef.current);

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onCloseRef.current();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      onCloseRef.current();
    }
  };

  return (
    <div className="modal-backdrop" onClick={handleBackdropClick} role="presentation">
      <div
        className={`modal ${size === "lg" ? "modal-lg" : ""}`.trim()}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
      >
        <header className="modal-header">
          <h2 id="modal-title">{title}</h2>
          <button
            ref={closeRef}
            type="button"
            className="btn icon"
            onClick={() => onCloseRef.current()}
            aria-label={labels.cancel}
          >
            ×
          </button>
        </header>
        <div ref={bodyRef} className="modal-body">
          {children}
        </div>
      </div>
    </div>
  );
}
