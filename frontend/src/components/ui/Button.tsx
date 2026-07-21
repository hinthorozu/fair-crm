import React from "react";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "link";
export type ButtonSize = "sm" | "md" | "lg";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  /** Renders as danger-colored link when variant="link". */
  danger?: boolean;
}

const VARIANT_CLASS: Record<ButtonVariant, string> = {
  primary: "btn primary",
  secondary: "btn secondary",
  ghost: "btn ghost",
  danger: "btn danger",
  link: "btn link",
};

const SIZE_CLASS: Record<ButtonSize, string> = {
  sm: "btn-sm",
  md: "",
  lg: "btn-lg",
};

/**
 * Shared text button primitive.
 * Prefer this over ad-hoc `<button className="btn …">` for new code;
 * existing class-based buttons remain supported by the same CSS tokens.
 */
export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    variant = "secondary",
    size = "md",
    loading = false,
    danger = false,
    className = "",
    type = "button",
    disabled,
    children,
    ...rest
  },
  ref,
) {
  const isDisabled = Boolean(disabled || loading);
  return (
    <button
      ref={ref}
      type={type}
      className={[
        VARIANT_CLASS[variant],
        SIZE_CLASS[size],
        danger && variant === "link" ? "danger" : "",
        loading ? "btn--loading" : "",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      disabled={isDisabled}
      aria-busy={loading || undefined}
      {...rest}
    >
      {children}
    </button>
  );
});
