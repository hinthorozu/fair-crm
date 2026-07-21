import React from "react";
import { labels } from "../../labels";
import { uiLabels } from "../../labels/uiLabels";
import { ConfirmDialog } from "./ConfirmDialog";

/** Overlay dialog — ADR-028 Universal Modal Standard (no backdrop/Escape close; dirty guard). */
interface ModalProps {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
  size?: "default" | "md" | "lg";
  className?: string;
  /** Sticky action footer (visible on mobile bottom-sheet — ADR-032). */
  footer?: React.ReactNode;
}

const FOCUSABLE_SELECTOR =
  'textarea, input:not([type="hidden"]), select, button:not([disabled]), [href], [tabindex]:not([tabindex="-1"])';

type ModalDirtySetter = (dirty: boolean) => void;

const ModalDirtyContext = React.createContext<ModalDirtySetter | null>(null);
const ModalCloseContext = React.createContext<(() => void) | null>(null);

export function useModalDirty(): ModalDirtySetter {
  const setter = React.useContext(ModalDirtyContext);
  return React.useCallback((dirty: boolean) => setter?.(dirty), [setter]);
}

export function useModalRequestClose(fallback: () => void): () => void {
  const requestClose = React.useContext(ModalCloseContext);
  return React.useCallback(() => {
    if (requestClose) requestClose();
    else fallback();
  }, [requestClose, fallback]);
}

function focusInitialElement(body: HTMLElement | null, closeButton: HTMLButtonElement | null) {
  const firstFocusable = body?.querySelector<HTMLElement>(FOCUSABLE_SELECTOR);
  if (firstFocusable) {
    firstFocusable.focus();
    return;
  }
  closeButton?.focus();
}

export function Modal({ title, onClose, children, size = "default", className, footer }: ModalProps) {
  const closeRef = React.useRef<HTMLButtonElement>(null);
  const bodyRef = React.useRef<HTMLDivElement>(null);
  const onCloseRef = React.useRef(onClose);
  onCloseRef.current = onClose;

  const [dirty, setDirty] = React.useState(false);
  const [showDiscardConfirm, setShowDiscardConfirm] = React.useState(false);

  const requestClose = React.useCallback(() => {
    if (dirty) {
      setShowDiscardConfirm(true);
      return;
    }
    onCloseRef.current();
  }, [dirty]);

  const confirmDiscard = React.useCallback(() => {
    setShowDiscardConfirm(false);
    setDirty(false);
    onCloseRef.current();
  }, []);

  const cancelDiscard = React.useCallback(() => {
    setShowDiscardConfirm(false);
  }, []);

  const setModalDirty = React.useCallback<ModalDirtySetter>((value) => {
    setDirty(value);
  }, []);

  React.useEffect(() => {
    focusInitialElement(bodyRef.current, closeRef.current);
  }, []);

  return (
    <>
      <div className="modal-backdrop" role="presentation">
        <div
          className={`modal ${size === "lg" ? "modal-lg" : size === "md" ? "modal-md" : ""} ${className ?? ""}`.trim()}
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
              onClick={requestClose}
              aria-label={labels.cancel}
            >
              ×
            </button>
          </header>
          <ModalDirtyContext.Provider value={setModalDirty}>
            <ModalCloseContext.Provider value={requestClose}>
              <div ref={bodyRef} className="modal-body">
                {children}
              </div>
              {footer ? <div className="modal-footer">{footer}</div> : null}
            </ModalCloseContext.Provider>
          </ModalDirtyContext.Provider>
        </div>
      </div>

      {showDiscardConfirm && (
        <ConfirmDialog
          className="modal-backdrop-nested"
          title={uiLabels.modalUnsavedTitle}
          message={uiLabels.modalUnsavedMessage}
          cancelLabel={uiLabels.modalReturnToForm}
          confirmLabel={uiLabels.modalDiscardExit}
          variant="danger"
          onCancel={cancelDiscard}
          onConfirm={confirmDiscard}
        />
      )}
    </>
  );
}
