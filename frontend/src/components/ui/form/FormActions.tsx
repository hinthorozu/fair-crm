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
      <button type="button" className="btn secondary" onClick={onCancel} disabled={saving}>
        {cancelLabel}
      </button>
      <button type="submit" className="btn primary" disabled={saving}>
        {saving ? (savingLabel ?? "…") : submitLabel}
      </button>
    </div>
  );
}
