import React from "react";

interface FormFieldProps {
  label: string;
  htmlFor: string;
  required?: boolean;
  hint?: string;
  error?: string;
  fullWidth?: boolean;
  children: React.ReactNode;
}

export function FormField({
  label,
  htmlFor,
  required,
  hint,
  error,
  fullWidth,
  children,
}: FormFieldProps) {
  return (
    <div className={`field ${fullWidth ? "span-2" : ""}`.trim()}>
      <label htmlFor={htmlFor}>
        <span className="field-label">
          {label}
          {required && <span className="field-required" aria-hidden="true"> *</span>}
        </span>
        {children}
      </label>
      {hint && !error && <span className="field-hint">{hint}</span>}
      {error && <span className="field-error" role="alert">{error}</span>}
    </div>
  );
}

interface FormActionsProps {
  onCancel: () => void;
  submitLabel: string;
  cancelLabel: string;
  saving?: boolean;
}

export function FormActions({ onCancel, submitLabel, cancelLabel, saving }: FormActionsProps) {
  return (
    <div className="form-actions span-2">
      <button type="button" className="btn secondary" onClick={onCancel} disabled={saving}>
        {cancelLabel}
      </button>
      <button type="submit" className="btn primary" disabled={saving}>
        {saving ? "…" : submitLabel}
      </button>
    </div>
  );
}
