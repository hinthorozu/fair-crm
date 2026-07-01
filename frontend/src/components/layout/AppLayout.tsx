import React from "react";
import { Breadcrumb, type BreadcrumbItem } from "../ui/Breadcrumb";
import { labels } from "../../labels";
import { config } from "../../config";

interface NavItem {
  path: string;
  label: string;
  active: boolean;
  onClick: (e: React.MouseEvent) => void;
}

interface AppLayoutProps {
  children: React.ReactNode;
  breadcrumbs?: BreadcrumbItem[];
  navItems: NavItem[];
  sidebarOpen?: boolean;
  onToggleSidebar?: () => void;
}

export function AppLayout({
  children,
  breadcrumbs = [],
  navItems,
  sidebarOpen = false,
  onToggleSidebar,
}: AppLayoutProps) {
  return (
    <div className={`app-shell ${sidebarOpen ? "sidebar-open" : ""}`}>
      <aside className="sidebar" aria-label="Ana menü">
        <div className="sidebar-brand">
          <span className="brand">{labels.appTitle}</span>
        </div>
        <nav className="sidebar-nav">
          {navItems.map((item) => (
            <a
              key={item.path}
              href={item.path}
              className={item.active ? "sidebar-link active" : "sidebar-link"}
              onClick={item.onClick}
              aria-current={item.active ? "page" : undefined}
            >
              {item.label}
            </a>
          ))}
        </nav>
      </aside>

      <div className="app-main">
        <header className="app-topbar">
          <div className="app-topbar-left">
            {onToggleSidebar && (
              <button
                type="button"
                className="btn icon sidebar-toggle"
                onClick={onToggleSidebar}
                aria-label="Menüyü aç/kapat"
              >
                ☰
              </button>
            )}
            {breadcrumbs.length > 0 && <Breadcrumb items={breadcrumbs} />}
          </div>
          <span className="env-badge">Dev bypass · {config.organizationId.slice(0, 8)}…</span>
        </header>

        <main className="app-content">{children}</main>
      </div>

      {sidebarOpen && (
        <button
          type="button"
          className="sidebar-overlay"
          aria-label="Menüyü kapat"
          onClick={onToggleSidebar}
        />
      )}
    </div>
  );
}
