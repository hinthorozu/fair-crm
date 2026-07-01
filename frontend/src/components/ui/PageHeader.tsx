import React from "react";

interface PageHeaderProps {
  title: string;
  subtitle?: React.ReactNode;
  actions?: React.ReactNode;
  backAction?: React.ReactNode;
}

export function PageHeader({ title, subtitle, actions, backAction }: PageHeaderProps) {
  return (
    <header className="page-header">
      <div className="page-header-content">
        {backAction}
        <h1>{title}</h1>
        {subtitle && <p className="page-header-subtitle muted">{subtitle}</p>}
      </div>
      {actions && <div className="page-header-actions">{actions}</div>}
    </header>
  );
}
