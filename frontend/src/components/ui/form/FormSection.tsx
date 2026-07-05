import React from "react";

interface FormSectionProps {
  title: string;
  children: React.ReactNode;
  className?: string;
}

export function FormSection({ title, children, className }: FormSectionProps) {
  const sectionId = React.useId();
  return (
    <section
      className={`form-section ${className ?? ""}`.trim()}
      aria-labelledby={sectionId}
    >
      <h3 id={sectionId} className="form-section-title">
        {title}
      </h3>
      {children}
    </section>
  );
}
