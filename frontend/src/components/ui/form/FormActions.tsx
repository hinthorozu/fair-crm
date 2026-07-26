import { Button } from "../Button";

interface FormActionsProps {
  onCancel: () => void;
  submitLabel: string;
  cancelLabel: string;
  saving?: boolean;
  savingLabel?: string;
  /** When true, primary submit is disabled (in addition to saving/loading). */
  submitDisabled?: boolean;
  /** Optional second submit (e.g. "Kaydet ve Yeni") — only shown when both props are set. */
  secondarySubmitLabel?: string;
  onSecondarySubmit?: () => void;
}

export function FormActions({
  onCancel,
  submitLabel,
  cancelLabel,
  saving,
  savingLabel,
  submitDisabled = false,
  secondarySubmitLabel,
  onSecondarySubmit,
}: FormActionsProps) {
  const showSecondary = Boolean(secondarySubmitLabel && onSecondarySubmit);

  return (
    <div className="form-actions span-2">
      <Button type="button" variant="secondary" onClick={onCancel} disabled={saving}>
        {cancelLabel}
      </Button>
      {showSecondary ? (
        <Button
          type="button"
          variant="secondary"
          onClick={onSecondarySubmit}
          disabled={submitDisabled || saving}
        >
          {saving ? (savingLabel ?? "…") : secondarySubmitLabel}
        </Button>
      ) : null}
      <Button type="submit" variant="primary" loading={saving} disabled={submitDisabled || saving}>
        {saving ? (savingLabel ?? "…") : submitLabel}
      </Button>
    </div>
  );
}
