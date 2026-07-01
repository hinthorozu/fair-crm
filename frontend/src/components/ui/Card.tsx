import React from "react";

interface CardProps {
  children: React.ReactNode;
  className?: string;
  padding?: "none" | "default";
}

export function Card({ children, className = "", padding = "default" }: CardProps) {
  return (
    <div className={`card card-padding-${padding} ${className}`.trim()}>
      {children}
    </div>
  );
}
