import React from "react";
import { NavIconEye, NavIconEyeOff } from "../../layout/NavIcons";
import { uiLabels } from "../../../labels/uiLabels";
import { IconButton } from "../IconButton";

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
        <IconButton
          variant="password"
          label={visible ? uiLabels.hidePassword : uiLabels.showPassword}
          icon={visible ? <NavIconEyeOff /> : <NavIconEye />}
          disabled={disabled}
          pressed={visible}
          onMouseDown={(event) => event.preventDefault()}
          onClick={toggleVisibility}
        />
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

export interface CheckboxFieldProps {
  id: string;
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  hint?: string;
  className?: string;
  inputClassName?: string;
  /** Hide visible label (still associated via htmlFor / aria). */
  hideLabel?: boolean;
  ariaLabel?: string;
  indeterminate?: boolean;
  inputRef?: React.Ref<HTMLInputElement>;
}

export function CheckboxField({
  id,
  label,
  checked,
  onChange,
  disabled,
  hint,
  className,
  inputClassName,
  hideLabel = false,
  ariaLabel,
  indeterminate = false,
  inputRef,
}: CheckboxFieldProps) {
  const localRef = React.useRef<HTMLInputElement | null>(null);

  const setRefs = React.useCallback(
    (node: HTMLInputElement | null) => {
      localRef.current = node;
      if (typeof inputRef === "function") {
        inputRef(node);
      } else if (inputRef) {
        (inputRef as React.MutableRefObject<HTMLInputElement | null>).current = node;
      }
    },
    [inputRef],
  );

  React.useEffect(() => {
    if (localRef.current) {
      localRef.current.indeterminate = indeterminate;
    }
  }, [indeterminate]);

  const input = (
    <input
      ref={setRefs}
      id={id}
      type="checkbox"
      className={inputClassName}
      checked={checked}
      disabled={disabled}
      onChange={(event) => onChange(event.target.checked)}
      aria-label={ariaLabel ?? (hideLabel ? label : undefined)}
    />
  );

  if (hideLabel && !hint) {
    return (
      <span className={["checkbox-field-control", className].filter(Boolean).join(" ")}>
        {input}
        <label htmlFor={id} className="sr-only">
          {label}
        </label>
      </span>
    );
  }

  return (
    <div className={["field", "checkbox-field", className].filter(Boolean).join(" ")}>
      {input}
      <div className="checkbox-field-content">
        <label htmlFor={id} className={hideLabel ? "sr-only" : "checkbox-field-label"}>
          {label}
        </label>
        {hint ? <span className="field-hint">{hint}</span> : null}
      </div>
    </div>
  );
}

export interface RadioFieldProps {
  id: string;
  name: string;
  label: string;
  value: string;
  checked: boolean;
  onChange: (value: string) => void;
  disabled?: boolean;
  hint?: string;
  className?: string;
  inputClassName?: string;
  hideLabel?: boolean;
  ariaLabel?: string;
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
  className,
  inputClassName,
  hideLabel = false,
  ariaLabel,
}: RadioFieldProps) {
  const input = (
    <input
      id={id}
      type="radio"
      name={name}
      value={value}
      className={inputClassName}
      checked={checked}
      disabled={disabled}
      onChange={() => onChange(value)}
      aria-label={ariaLabel ?? (hideLabel ? label : undefined)}
    />
  );

  if (hideLabel && !hint) {
    return (
      <span className={["radio-field-control", className].filter(Boolean).join(" ")}>
        {input}
        <label htmlFor={id} className="sr-only">
          {label}
        </label>
      </span>
    );
  }

  return (
    <div className={["field", "radio-field", className].filter(Boolean).join(" ")}>
      {input}
      <div className="checkbox-field-content">
        <label htmlFor={id} className={hideLabel ? "sr-only" : "checkbox-field-label"}>
          {label}
        </label>
        {hint ? <span className="field-hint">{hint}</span> : null}
      </div>
    </div>
  );
}
