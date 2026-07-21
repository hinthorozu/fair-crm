import { Button } from "../Button";

interface FormActionsProps {
  onCancel: () => void;
  submitLabel: string;
  cancelLabel: string;
  saving?: boolean;
  savingLabel?: string;
}

export function FormActions({
  onCancel,
  submitLabel,
  cancelLabel,
  saving,
  savingLabel,
}: FormActionsProps) {
  return (
    <div className="form-actions span-2">
      <Button type="button" variant="secondary" onClick={onCancel} disabled={saving}>
        {cancelLabel}
      </Button>
      <Button type="submit" variant="primary" loading={saving}>
        {saving ? (savingLabel ?? "…") : submitLabel}
      </Button>
    </div>
  );
}
