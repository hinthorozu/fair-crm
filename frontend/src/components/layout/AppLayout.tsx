import React from "react";
import { Breadcrumb, type BreadcrumbItem } from "../ui/Breadcrumb";
import { IconButton } from "../ui/IconButton";
import { labels } from "../../labels";
import { UserMenu } from "./UserMenu";
import { usePersistedCollapsed } from "../../hooks/usePersistedCollapsed";
import { SidebarCollapseButton } from "./SidebarCollapseButton";
import { SidebarTooltipTarget } from "./SidebarTooltip";
import { NavLink } from "./NavLink";
import { NavIconMenu } from "./NavIcons";

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
  onLogout: () => void | Promise<void>;
}

const MAIN_SIDEBAR_STORAGE_KEY = "fair-crm.sidebar.collapsed";

export function AppLayout({
  children,
  breadcrumbs = [],
  navItems,
  sidebarOpen = false,
  onToggleSidebar,
  onLogout,
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
            <SidebarTooltipTarget label={labels.appTitle} collapsed={sidebarCollapsed}>
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
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              variant="sidebar"
              href={item.path}
              label={item.label}
              icon={item.icon}
              active={item.active}
              collapsed={sidebarCollapsed}
              onClick={item.onClick}
            />
          ))}
        </nav>
      </aside>

      <div className="app-main">
        <header className="app-topbar">
          <div className="app-topbar-left">
            {onToggleSidebar && (
              <IconButton
                variant="ghost"
                className="sidebar-toggle"
                label="Menüyü aç/kapat"
                icon={<NavIconMenu />}
                onClick={onToggleSidebar}
              />
            )}
            {breadcrumbs.length > 0 && <Breadcrumb items={breadcrumbs} />}
          </div>
          <UserMenu onLogout={onLogout} />
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
