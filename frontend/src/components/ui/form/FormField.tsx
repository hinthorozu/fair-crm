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
          {required && (
            <span className="field-required" aria-hidden="true">
              {" "}
              *
            </span>
          )}
        </span>
        {children}
      </label>
      {hint && !error ? <span className="field-hint">{hint}</span> : null}
      {error ? (
        <span className="field-error" role="alert">
          {error}
        </span>
      ) : null}
    </div>
  );
}
