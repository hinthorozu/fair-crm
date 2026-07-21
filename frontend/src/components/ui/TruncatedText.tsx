import React from "react";

export interface TruncatedTextProps {
  value: string | null | undefined;
  /** Max visible characters before ellipsis. Default 24. */
  maxLength?: number;
  /** Use monospace styling (UUID / technical ids). */
  mono?: boolean;
  empty?: string;
  className?: string;
}

/** Short display + full value in `title` for UUID / URL / long text (ADR-032). */
export function TruncatedText({
  value,
  maxLength = 24,
  mono = false,
  empty = "—",
  className = "",
}: TruncatedTextProps) {
  if (value == null || value === "") {
    return <span className={className}>{empty}</span>;
  }

  const needsTruncate = value.length > maxLength;
  const display = needsTruncate ? `${value.slice(0, maxLength)}…` : value;
  const classes = ["text-wrap", mono ? "text-mono" : "", className].filter(Boolean).join(" ");

  return (
    <span className={classes} title={needsTruncate ? value : undefined}>
      {display}
    </span>
  );
}
