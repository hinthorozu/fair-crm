import React from "react";
import { NavIconEye, NavIconEyeOff } from "../../layout/NavIcons";
import { uiLabels } from "../../../labels/uiLabels";

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

export interface PasswordInputProps extends Omit<TextInputProps, "type"> {}

export const PasswordInput = React.forwardRef<HTMLInputElement, PasswordInputProps>(
  function PasswordInput({ id, className, disabled, "aria-invalid": ariaInvalid, ...rest }, ref) {
    const [visible, setVisible] = React.useState(false);
    const inputRef = React.useRef<HTMLInputElement | null>(null);
    const selectionRef = React.useRef<{ start: number; end: number } | null>(null);

    const setRefs = React.useCallback(
      (node: HTMLInputElement | null) => {
        inputRef.current = node;
        if (typeof ref === "function") {
          ref(node);
        } else if (ref) {
          ref.current = node;
        }
      },
      [ref],
    );

    React.useLayoutEffect(() => {
      const input = inputRef.current;
      const selection = selectionRef.current;
      if (!input || !selection || document.activeElement !== input) {
        selectionRef.current = null;
        return;
      }
      input.setSelectionRange(selection.start, selection.end);
      selectionRef.current = null;
    }, [visible]);

    const toggleVisibility = () => {
      const input = inputRef.current;
      if (input) {
        selectionRef.current = {
          start: input.selectionStart ?? input.value.length,
          end: input.selectionEnd ?? input.value.length,
        };
      }
      setVisible((current) => !current);
    };

    return (
      <div className="password-input">
        <TextInput
          ref={setRefs}
          id={id}
          type={visible ? "text" : "password"}
          className={["password-input__control", className].filter(Boolean).join(" ")}
          disabled={disabled}
          aria-invalid={ariaInvalid}
          {...rest}
        />
        <button
          type="button"
          className="password-input__toggle"
          disabled={disabled}
          aria-label={visible ? uiLabels.hidePassword : uiLabels.showPassword}
          aria-pressed={visible}
          onMouseDown={(event) => event.preventDefault()}
          onClick={toggleVisibility}
        >
          {visible ? <NavIconEyeOff /> : <NavIconEye />}
        </button>
      </div>
    );
  },
);

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

interface RadioFieldProps {
  id: string;
  name: string;
  label: string;
  value: string;
  checked: boolean;
  onChange: (value: string) => void;
  disabled?: boolean;
  hint?: string;
}

export function RadioField({
  id,
  name,
  label,
  value,
  checked,
  onChange,
  disabled,
  hint,
}: RadioFieldProps) {
  return (
    <div className="field radio-field">
      <input
        id={id}
        type="radio"
        name={name}
        value={value}
        checked={checked}
        disabled={disabled}
        onChange={() => onChange(value)}
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
