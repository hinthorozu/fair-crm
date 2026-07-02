import React from "react";
import { useModalDirty, useModalRequestClose } from "../components/ui/Modal";

function serializeFormValues<T>(value: T): string {
  return JSON.stringify(value);
}

/** Report whether the current form values differ from the baseline (modal dirty guard). */
export function useReportFormDirty<T>(values: T, baseline: T): void {
  const setDirty = useModalDirty();

  React.useEffect(() => {
    setDirty(serializeFormValues(values) !== serializeFormValues(baseline));
  }, [values, baseline, setDirty]);

  React.useEffect(() => () => setDirty(false), [setDirty]);
}

/** Cancel handler that respects modal unsaved-change guard when inside a Modal. */
export function useModalFormCancel(onCancel: () => void): () => void {
  return useModalRequestClose(onCancel);
}
