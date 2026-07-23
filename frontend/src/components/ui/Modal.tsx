import React from "react";
import { labels } from "../../labels";
import { NavIconClose } from "../layout/NavIcons";
import {
  FormDirtyHost,
  useFormDirtyRequestClose,
  useFormDirtySetter,
  useHasFormDirtyHost,
} from "./form/FormDirty";
import { IconButton } from "./IconButton";

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

/** @deprecated Prefer useFormDirtySetter from form/FormDirty — kept for Modal consumers. */
export function useModalDirty(): (dirty: boolean) => void {
  return useFormDirtySetter();
}

/** @deprecated Prefer useFormDirtyRequestClose from form/FormDirty. */
export function useModalRequestClose(fallback: () => void): () => void {
  return useFormDirtyRequestClose(fallback);
}

function focusInitialElement(body: HTMLElement | null, closeButton: HTMLButtonElement | null) {
  const firstFocusable = body?.querySelector<HTMLElement>(FOCUSABLE_SELECTOR);
  if (firstFocusable) {
    firstFocusable.focus();
    return;
  }
  closeButton?.focus();
}

function ModalChrome({
  title,
  children,
  size = "default",
  className,
  footer,
}: Omit<ModalProps, "onClose">) {
  const closeRef = React.useRef<HTMLButtonElement>(null);
  const bodyRef = React.useRef<HTMLDivElement>(null);
  const requestClose = useFormDirtyRequestClose(() => undefined);

  React.useEffect(() => {
    focusInitialElement(bodyRef.current, closeRef.current);
  }, []);

  return (
    <div className="modal-backdrop" role="presentation">
      <div
        className={`modal ${size === "lg" ? "modal-lg" : size === "md" ? "modal-md" : ""} ${className ?? ""}`.trim()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
      >
        <header className="modal-header">
          <h2 id="modal-title">{title}</h2>
          <IconButton
            ref={closeRef}
            label={labels.cancel}
            icon={<NavIconClose />}
            onClick={requestClose}
          />
        </header>
        <div ref={bodyRef} className="modal-body">
          {children}
        </div>
        {footer ? <div className="modal-footer">{footer}</div> : null}
      </div>
    </div>
  );
}

export function Modal({ title, onClose, children, size = "default", className, footer }: ModalProps) {
  const nestedInDirtyHost = useHasFormDirtyHost();
  const chrome = (
    <ModalChrome title={title} size={size} className={className} footer={footer}>
      {children}
    </ModalChrome>
  );

  // Allow wrapper modals to own FormDirtyHost above Modal so hooks can run in the parent tree.
  if (nestedInDirtyHost) return chrome;

  return (
    <FormDirtyHost onClose={onClose} confirmClassName="modal-backdrop-nested">
      {chrome}
    </FormDirtyHost>
  );
}
