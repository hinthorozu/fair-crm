import React from "react";

export type PageHeaderActionVariant = "primary" | "secondary" | "danger";

export interface PageHeaderAction {
  id: string;
  label: string;
  onClick: () => void;
  variant?: PageHeaderActionVariant;
  disabled?: boolean;
  loading?: boolean;
  title?: string;
}

export interface PageHeaderBreadcrumb {
  label: string;
  onClick?: () => void;
  current?: boolean;
}

interface PageHeaderProps {
  title: string;
  subtitle?: React.ReactNode;
  breadcrumbs?: PageHeaderBreadcrumb[];
  actions?: PageHeaderAction[] | React.ReactNode;
  /** @deprecated Prefer breadcrumbs */
  backAction?: React.ReactNode;
}

function actionButtonClass(variant: PageHeaderActionVariant = "secondary"): string {
  if (variant === "primary") return "btn primary";
  if (variant === "danger") return "btn danger";
  return "btn secondary";
}

function isActionArray(actions: PageHeaderAction[] | React.ReactNode): actions is PageHeaderAction[] {
  return Array.isArray(actions);
}

function renderActions(actions: PageHeaderAction[] | React.ReactNode | undefined): React.ReactNode {
  if (!actions) return null;
  if (!isActionArray(actions)) return actions;
  if (actions.length === 0) return null;
  return actions.map((action) => (
    <button
      key={action.id}
      type="button"
      className={actionButtonClass(action.variant)}
      onClick={action.onClick}
      disabled={action.disabled || action.loading}
      title={action.title}
    >
      {action.loading ? "…" : action.label}
    </button>
  ));
}

function renderBackLink(
  breadcrumbs: PageHeaderBreadcrumb[] | undefined,
  backAction: React.ReactNode | undefined,
): React.ReactNode {
  if (breadcrumbs?.length) {
    const back = breadcrumbs.find((item) => item.onClick && !item.current) ?? breadcrumbs[0];
    if (back?.onClick) {
      return (
        <button type="button" className="btn link back-link" onClick={back.onClick}>
          ← {back.label}
        </button>
      );
    }
  }
  return backAction ?? null;
}

export function PageHeader({ title, subtitle, breadcrumbs, actions, backAction }: PageHeaderProps) {
  const renderedActions = renderActions(actions);
  const backLink = renderBackLink(breadcrumbs, backAction);

  return (
    <header className="page-header">
      <div className="page-header-top">
        <div className="page-header-content">
          {backLink}
          <h1>{title}</h1>
          {subtitle && <p className="page-header-subtitle muted">{subtitle}</p>}
        </div>
      </div>
      {renderedActions && (
        <>
          <hr className="page-header-divider" aria-hidden="true" />
          <div className="page-header-actions">{renderedActions}</div>
        </>
      )}
    </header>
  );
}
