import React from "react";
import { uiLabels } from "../../../labels/uiLabels";
import { ConfirmDialog } from "../ConfirmDialog";

/**
 * Universal dirty-form guard (ADR-028 extended).
 * Used by Modal, Drawer, page forms, and wizards. Registers with the
 * navigation dirty gate so sidebar / route / browser leave also confirm.
 */

type DirtySetter = (dirty: boolean) => void;

const FormDirtySetContext = React.createContext<DirtySetter | null>(null);
const FormDirtyCloseContext = React.createContext<(() => void) | null>(null);

const navigationDirtySources = new Map<string, true>();
const navigationDirtyListeners = new Set<() => void>();

function notifyNavigationDirtyListeners() {
  navigationDirtyListeners.forEach((listener) => listener());
}

/** Register/unregister a dirty source for app-level navigation blocking. */
export function setNavigationDirtySource(sourceId: string, dirty: boolean): void {
  if (dirty) navigationDirtySources.set(sourceId, true);
  else navigationDirtySources.delete(sourceId);
  notifyNavigationDirtyListeners();
}

export function isNavigationDirty(): boolean {
  return navigationDirtySources.size > 0;
}

export function subscribeNavigationDirty(listener: () => void): () => void {
  navigationDirtyListeners.add(listener);
  return () => {
    navigationDirtyListeners.delete(listener);
  };
}

/** Clear all navigation dirty sources after a confirmed discard + leave. */
export function clearNavigationDirtySources(): void {
  if (navigationDirtySources.size === 0) return;
  navigationDirtySources.clear();
  notifyNavigationDirtyListeners();
}

export function useFormDirtySetter(): DirtySetter {
  const setter = React.useContext(FormDirtySetContext);
  return React.useCallback((dirty: boolean) => setter?.(dirty), [setter]);
}

export function useFormDirtyRequestClose(fallback: () => void): () => void {
  const requestClose = React.useContext(FormDirtyCloseContext);
  return React.useCallback(() => {
    if (requestClose) requestClose();
    else fallback();
  }, [requestClose, fallback]);
}

/** True when rendered under a FormDirtyHost (Modal may skip nesting another host). */
export function useHasFormDirtyHost(): boolean {
  return React.useContext(FormDirtyCloseContext) != null;
}

function serializeFormValues<T>(value: T): string {
  return JSON.stringify(value);
}

/** Report whether current form values differ from the baseline. */
export function useReportFormDirty<T>(values: T, baseline: T): void {
  const setDirty = useFormDirtySetter();

  React.useEffect(() => {
    setDirty(serializeFormValues(values) !== serializeFormValues(baseline));
  }, [values, baseline, setDirty]);

  React.useEffect(() => () => setDirty(false), [setDirty]);
}

/** Cancel / leave handler that respects the nearest FormDirtyHost. */
export function useFormDirtyCancel(onCancel: () => void): () => void {
  return useFormDirtyRequestClose(onCancel);
}

interface FormDirtyHostProps {
  onClose: () => void;
  children: React.ReactNode;
  /** When false, host does not block (e.g. read-only shell). Default true. */
  enabled?: boolean;
  /** Extra class for the discard ConfirmDialog backdrop (e.g. modal nested). */
  confirmClassName?: string;
}

/**
 * Owns dirty state + discard confirm for a form surface (modal, drawer, page, wizard).
 * Also registers with the navigation dirty gate while dirty.
 */
export function FormDirtyHost({
  onClose,
  children,
  enabled = true,
  confirmClassName,
}: FormDirtyHostProps) {
  const sourceId = React.useId();
  const onCloseRef = React.useRef(onClose);
  onCloseRef.current = onClose;

  const [dirty, setDirty] = React.useState(false);
  const [showDiscardConfirm, setShowDiscardConfirm] = React.useState(false);

  const effectiveDirty = enabled && dirty;

  React.useEffect(() => {
    setNavigationDirtySource(sourceId, effectiveDirty);
    return () => setNavigationDirtySource(sourceId, false);
  }, [sourceId, effectiveDirty]);

  const requestClose = React.useCallback(() => {
    if (effectiveDirty) {
      setShowDiscardConfirm(true);
      return;
    }
    onCloseRef.current();
  }, [effectiveDirty]);

  const confirmDiscard = React.useCallback(() => {
    setShowDiscardConfirm(false);
    setDirty(false);
    setNavigationDirtySource(sourceId, false);
    onCloseRef.current();
  }, [sourceId]);

  const cancelDiscard = React.useCallback(() => {
    setShowDiscardConfirm(false);
  }, []);

  const setFormDirty = React.useCallback<DirtySetter>(
    (value) => {
      if (!enabled) {
        setDirty(false);
        return;
      }
      setDirty(value);
    },
    [enabled],
  );

  return (
    <FormDirtySetContext.Provider value={setFormDirty}>
      <FormDirtyCloseContext.Provider value={requestClose}>
        {children}
        {showDiscardConfirm ? (
          <DirtyDiscardConfirmDialog
            className={confirmClassName}
            onCancel={cancelDiscard}
            onConfirm={confirmDiscard}
          />
        ) : null}
      </FormDirtyCloseContext.Provider>
    </FormDirtySetContext.Provider>
  );
}

/** Canonical unsaved-changes confirm (shared copy + actions). */
export function DirtyDiscardConfirmDialog({
  onCancel,
  onConfirm,
  className,
}: {
  onCancel: () => void;
  onConfirm: () => void;
  className?: string;
}) {
  return (
    <ConfirmDialog
      className={className}
      title={uiLabels.modalUnsavedTitle}
      message={uiLabels.modalUnsavedMessage}
      cancelLabel={uiLabels.modalReturnToForm}
      confirmLabel={uiLabels.modalDiscardExit}
      variant="danger"
      onCancel={onCancel}
      onConfirm={onConfirm}
    />
  );
}

/**
 * App-level gate: blocks programmatic navigation / browser leave while any
 * FormDirtyHost reports dirty. Renders the same discard confirm.
 */
export function useNavigationDirtyGate(): {
  requestNavigation: (action: () => void) => void;
  confirmDialog: React.ReactNode;
} {
  const [pendingAction, setPendingAction] = React.useState<(() => void) | null>(null);
  const [, setTick] = React.useState(0);

  React.useEffect(() => subscribeNavigationDirty(() => setTick((n) => n + 1)), []);

  React.useEffect(() => {
    const onBeforeUnload = (event: BeforeUnloadEvent) => {
      if (!isNavigationDirty()) return;
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, []);

  const requestNavigation = React.useCallback((action: () => void) => {
    if (isNavigationDirty()) {
      setPendingAction(() => action);
      return;
    }
    action();
  }, []);

  const confirmDiscard = React.useCallback(() => {
    const action = pendingAction;
    setPendingAction(null);
    clearNavigationDirtySources();
    action?.();
  }, [pendingAction]);

  const cancelDiscard = React.useCallback(() => {
    setPendingAction(null);
  }, []);

  const confirmDialog =
    pendingAction != null ? (
      <DirtyDiscardConfirmDialog
        className="modal-backdrop-nested"
        onCancel={cancelDiscard}
        onConfirm={confirmDiscard}
      />
    ) : null;

  return { requestNavigation, confirmDialog };
}
