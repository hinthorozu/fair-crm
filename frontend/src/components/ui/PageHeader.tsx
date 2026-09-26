import React from "react";

export type PageHeaderActionVariant = "primary" | "secondary" | "danger";

export interface PageHeaderAction {
  id: string;
  label: string;
  onClick: () => void;
  /** When set, render real `<a href>` so middle/right-click can open a new tab. */
  href?: string;
  variant?: PageHeaderActionVariant;
  disabled?: boolean;
  loading?: boolean;
  title?: string;
}

export interface PageHeaderBreadcrumb {
  label: string;
  onClick?: () => void;
  /** When set, back link is a real `<a href>` (new-tab friendly). */
  href?: string;
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

function isPlainLeftClick(event: React.MouseEvent): boolean {
  return (
    !event.defaultPrevented &&
    event.button === 0 &&
    !event.metaKey &&
    !event.ctrlKey &&
    !event.shiftKey &&
    !event.altKey
  );
}

function isActionArray(actions: PageHeaderAction[] | React.ReactNode): actions is PageHeaderAction[] {
  return Array.isArray(actions);
}

function renderActions(actions: PageHeaderAction[] | React.ReactNode | undefined): React.ReactNode {
  if (!actions) return null;
  if (!isActionArray(actions)) return actions;
  if (actions.length === 0) return null;
  return actions.map((action) => {
    const className = actionButtonClass(action.variant);
    const label = action.loading ? "…" : action.label;
    const disabled = action.disabled || action.loading;
    if (action.href && !disabled) {
      return (
        <a
          key={action.id}
          href={action.href}
          className={className}
          title={action.title}
          onClick={(event) => {
            if (!isPlainLeftClick(event)) return;
            event.preventDefault();
            action.onClick();
          }}
        >
          {label}
        </a>
      );
    }
    return (
      <button
        key={action.id}
        type="button"
        className={className}
        onClick={action.onClick}
        disabled={disabled}
        title={action.title}
      >
        {label}
      </button>
    );
  });
}

function renderBackLink(
  breadcrumbs: PageHeaderBreadcrumb[] | undefined,
  backAction: React.ReactNode | undefined,
): React.ReactNode {
  if (breadcrumbs?.length) {
    const back =
      breadcrumbs.find((item) => (item.onClick || item.href) && !item.current) ?? breadcrumbs[0];
    if (back?.href) {
      return (
        <a
          href={back.href}
          className="btn link back-link"
          onClick={(event) => {
            if (!back.onClick || !isPlainLeftClick(event)) return;
            event.preventDefault();
            back.onClick();
          }}
        >
          ← {back.label}
        </a>
      );
    }
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
