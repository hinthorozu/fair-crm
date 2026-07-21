import React from "react";

type CardElement = "div" | "section" | "aside";

export interface CardProps extends Omit<React.HTMLAttributes<HTMLElement>, "className"> {
  children: React.ReactNode;
  className?: string;
  padding?: "none" | "default";
  /** Semantic wrapper element; default `div`. */
  as?: CardElement;
}

/**
 * Shared surface container. Always applies the canonical `.card` class —
 * consumers must not add bare `className="card"` on raw elements.
 */
export function Card({
  children,
  className = "",
  padding = "default",
  as: Tag = "div",
  ...rest
}: CardProps) {
  return (
    <Tag
      className={["card", `card-padding-${padding}`, className].filter(Boolean).join(" ")}
      {...rest}
    >
      {children}
    </Tag>
  );
}
