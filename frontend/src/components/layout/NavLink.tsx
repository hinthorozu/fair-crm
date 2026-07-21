import React from "react";
import { withSidebarTooltip } from "./SidebarTooltip";

export type NavLinkVariant = "sidebar" | "di" | "admin";

export interface NavLinkProps {
  variant: NavLinkVariant;
  href?: string;
  label: string;
  icon: React.ReactNode;
  active?: boolean;
  disabled?: boolean;
  collapsed?: boolean;
  onClick?: (event: React.MouseEvent) => void;
  className?: string;
}

function classParts(variant: NavLinkVariant) {
  if (variant === "sidebar") {
    return { link: "sidebar-link", icon: "sidebar-link-icon", label: "sidebar-link-label" };
  }
  if (variant === "di") {
    return { link: "di-subnav-link", icon: "di-subnav-link-icon", label: "di-subnav-link-label" };
  }
  return { link: "admin-subnav-link", icon: "admin-subnav-link-icon", label: "admin-subnav-link-label" };
}

/**
 * Unified sidebar / nested-rail navigation item (P3).
 * Preserves layout-specific CSS class names while standardizing markup + a11y.
 */
export function NavLink({
  variant,
  href = "#",
  label,
  icon,
  active = false,
  disabled = false,
  collapsed = false,
  onClick,
  className = "",
}: NavLinkProps) {
  const parts = classParts(variant);
  const classes = [parts.link, active ? "active" : "", disabled ? "disabled" : "", className]
    .filter(Boolean)
    .join(" ");
  const content = (
    <>
      <span className={parts.icon} aria-hidden>
        {icon}
      </span>
      <span className={parts.label}>{label}</span>
    </>
  );

  const control = disabled ? (
    <button type="button" className={classes} onClick={onClick} aria-disabled="true">
      {content}
    </button>
  ) : (
    <a
      href={href}
      className={classes}
      onClick={onClick}
      aria-current={active ? "page" : undefined}
    >
      {content}
    </a>
  );

  return withSidebarTooltip(control, { label, collapsed });
}
