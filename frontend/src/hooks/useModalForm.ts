import {
  useFormDirtyCancel,
  useReportFormDirty,
} from "../components/ui/form/FormDirty";

export { useReportFormDirty };

/** Cancel handler that respects FormDirtyHost unsaved-change guard (Modal/Drawer/page). */
export function useModalFormCancel(onCancel: () => void): () => void {
  return useFormDirtyCancel(onCancel);
}
