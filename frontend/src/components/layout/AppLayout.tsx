import React from "react";
import { Breadcrumb, type BreadcrumbItem } from "../ui/Breadcrumb";
import { labels } from "../../labels";
import { config } from "../../config";
import { usePersistedCollapsed } from "../../hooks/usePersistedCollapsed";
import { SidebarCollapseButton } from "./SidebarCollapseButton";
import { withSidebarTooltip, SidebarTooltipTarget } from "./SidebarTooltip";

interface NavItem {
  path: string;
  label: string;
  icon: React.ReactNode;
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

const MAIN_SIDEBAR_STORAGE_KEY = "fair-crm.sidebar.collapsed";

export function AppLayout({
  children,
  breadcrumbs = [],
  navItems,
  sidebarOpen = false,
  onToggleSidebar,
}: AppLayoutProps) {
  const { collapsed: sidebarCollapsed, toggleCollapsed: toggleSidebarCollapsed } =
    usePersistedCollapsed(MAIN_SIDEBAR_STORAGE_KEY);

  return (
    <div
      className={`app-shell ${sidebarOpen ? "sidebar-open" : ""} ${
        sidebarCollapsed ? "sidebar-collapsed" : ""
      }`.trim()}
    >
      <aside
        className={`sidebar ${sidebarCollapsed ? "sidebar--collapsed" : ""}`}
        aria-label="Ana menü"
        aria-expanded={!sidebarCollapsed}
      >
        <div className="sidebar-header">
          {!sidebarCollapsed ? (
            <span className="brand">{labels.appTitle}</span>
          ) : (
            <SidebarTooltipTarget
              label={labels.appTitle}
              collapsed={sidebarCollapsed}
            >
              <span className="brand brand--icon">F</span>
            </SidebarTooltipTarget>
          )}
          <SidebarCollapseButton
            collapsed={sidebarCollapsed}
            onToggle={toggleSidebarCollapsed}
            className="sidebar-header-collapse-btn"
          />
        </div>
        <nav className="sidebar-nav">
          {navItems.map((item) =>
            withSidebarTooltip(
              <a
                key={item.path}
                href={item.path}
                className={item.active ? "sidebar-link active" : "sidebar-link"}
                onClick={item.onClick}
                aria-current={item.active ? "page" : undefined}
              >
                <span className="sidebar-link-icon">{item.icon}</span>
                <span className="sidebar-link-label">{item.label}</span>
              </a>,
              { label: item.label, collapsed: sidebarCollapsed },
            ),
          )}
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
