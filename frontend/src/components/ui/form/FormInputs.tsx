import React from "react";

type ControlProps = {
  id: string;
  className?: string;
  disabled?: boolean;
  "aria-invalid"?: boolean;
  "aria-describedby"?: string;
};

function controlClass(extra?: string, invalid?: boolean) {
  return ["form-control", invalid ? "form-control--invalid" : "", extra ?? ""]
    .filter(Boolean)
    .join(" ");
}

export interface TextInputProps
  extends ControlProps,
    Omit<React.InputHTMLAttributes<HTMLInputElement>, "id" | "className"> {}

export const TextInput = React.forwardRef<HTMLInputElement, TextInputProps>(function TextInput(
  { id, className, disabled, "aria-invalid": ariaInvalid, ...rest },
  ref,
) {
  return (
    <input
      ref={ref}
      id={id}
      disabled={disabled}
      aria-invalid={ariaInvalid}
      className={controlClass(className, ariaInvalid === true)}
      {...rest}
    />
  );
});

export interface SelectInputProps
  extends ControlProps,
    Omit<React.SelectHTMLAttributes<HTMLSelectElement>, "id" | "className"> {}

export const SelectInput = React.forwardRef<HTMLSelectElement, SelectInputProps>(
  function SelectInput({ id, className, disabled, "aria-invalid": ariaInvalid, children, ...rest }, ref) {
    return (
      <select
        ref={ref}
        id={id}
        disabled={disabled}
        aria-invalid={ariaInvalid}
        className={controlClass(className, ariaInvalid === true)}
        {...rest}
      >
        {children}
      </select>
    );
  },
);

export interface TextareaInputProps
  extends ControlProps,
    Omit<React.TextareaHTMLAttributes<HTMLTextAreaElement>, "id" | "className"> {}

export const TextareaInput = React.forwardRef<HTMLTextAreaElement, TextareaInputProps>(
  function TextareaInput({ id, className, disabled, "aria-invalid": ariaInvalid, ...rest }, ref) {
    return (
      <textarea
        ref={ref}
        id={id}
        disabled={disabled}
        aria-invalid={ariaInvalid}
        className={controlClass(`form-control-textarea ${className ?? ""}`.trim(), ariaInvalid === true)}
        {...rest}
      />
    );
  },
);

interface CheckboxFieldProps {
  id: string;
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  hint?: string;
}

export function CheckboxField({ id, label, checked, onChange, disabled, hint }: CheckboxFieldProps) {
  return (
    <div className="field checkbox-field">
      <input
        id={id}
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(event) => onChange(event.target.checked)}
      />
      <div className="checkbox-field-content">
        <label htmlFor={id} className="checkbox-field-label">
          {label}
        </label>
        {hint ? <span className="field-hint">{hint}</span> : null}
      </div>
    </div>
  );
}
