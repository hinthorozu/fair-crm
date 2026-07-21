import React from "react";

export type BannerVariant = "success" | "warning" | "error" | "info";

export interface BannerProps {
  children: React.ReactNode;
  variant: BannerVariant;
  className?: string;
  /** Defaults: error → alert; others → status. */
  role?: "status" | "alert";
  as?: "div" | "p";
}

/**
 * Shared page/form notification surface (ADR-032).
 * Renders the canonical `.banner` + variant classes; do not invent parallel toast systems.
 */
export function Banner({
  children,
  variant,
  className = "",
  role,
  as: Tag = "div",
}: BannerProps) {
  const resolvedRole = role ?? (variant === "error" ? "alert" : "status");
  return (
    <Tag className={["banner", variant, className].filter(Boolean).join(" ")} role={resolvedRole}>
      {children}
    </Tag>
  );
}
