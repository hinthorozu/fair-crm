import React from "react";

export type IconButtonVariant = "ghost" | "bordered" | "table" | "kebab" | "password";

export interface IconButtonProps
  extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, "children" | "aria-label" | "className"> {
  /** Required accessible name (aria-label). */
  label: string;
  icon: React.ReactNode;
  variant?: IconButtonVariant;
  /** Maps to aria-pressed when provided. */
  pressed?: boolean;
  /** Disables the control and sets aria-busy. */
  loading?: boolean;
  className?: string;
}

const VARIANT_CLASS: Record<IconButtonVariant, string> = {
  ghost: "btn icon",
  bordered: "sidebar-collapse-btn",
  table: "table-expand-btn",
  kebab: "btn btn-sm icon kebab-menu-btn",
  password: "password-input__toggle",
};

/**
 * Shared icon-only control (P3 shell chrome).
 * Prefer this over bare icon `<button>` markup in shell / overlays / tables.
 */
export const IconButton = React.forwardRef<HTMLButtonElement, IconButtonProps>(function IconButton(
  {
    label,
    icon,
    variant = "ghost",
    pressed,
    loading = false,
    className = "",
    type = "button",
    disabled,
    title,
    ...rest
  },
  ref,
) {
  const isDisabled = Boolean(disabled || loading);
  return (
    <button
      ref={ref}
      type={type}
      className={[VARIANT_CLASS[variant], className].filter(Boolean).join(" ")}
      aria-label={label}
      aria-pressed={pressed}
      aria-busy={loading || undefined}
      title={title ?? label}
      disabled={isDisabled}
      {...rest}
    >
      {icon}
    </button>
  );
});
