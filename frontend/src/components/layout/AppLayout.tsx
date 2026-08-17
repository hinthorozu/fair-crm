import React from "react";
import { useAuth } from "../../auth/AuthContext";
import { config } from "../../config";
import { labels } from "../../labels";
import { uiLabels } from "../../labels/uiLabels";
import {
  canAccessApplicationPath,
  canAccessMainNavigation,
  firstAccessibleAdminPath,
  firstAccessibleDataIntegrationPath,
} from "../../permissions/navigationPermissions";
import { usePersistedCollapsed } from "../../hooks/usePersistedCollapsed";
import { Breadcrumb, type BreadcrumbItem } from "../ui/Breadcrumb";
import { EmptyState } from "../ui/EmptyState";
import { IconButton } from "../ui/IconButton";
import { PageHeader } from "../ui/PageHeader";
import { PageShell } from "../ui/PageShell";
import { NavIconMenu } from "./NavIcons";
import { NavLink } from "./NavLink";
import { SidebarCollapseButton } from "./SidebarCollapseButton";
import { SidebarTooltipTarget } from "./SidebarTooltip";
import { UserMenu } from "./UserMenu";

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

function mainNavigationSection(path: string): string {
  if (path.startsWith("/admin")) return "/admin";
  if (path.startsWith("/data-integration") || path.startsWith("/imports")) {
    return "/data-integration";
  }
  if (path.startsWith("/customers")) return "/customers";
  if (path.startsWith("/fairs")) return "/fairs";
  if (path.startsWith("/todos")) return "/todos";
  if (path.startsWith("/operations")) return "/operations";
  if (path.startsWith("/activities")) return "/activities";
  return path;
}

function pushInternalNavigation(path: string, event: React.MouseEvent): void {
  event.preventDefault();
  if (`${window.location.pathname}${window.location.search}` !== path) {
    window.history.pushState(null, "", path);
  }
  window.dispatchEvent(new PopStateEvent("popstate"));
}

export function AppLayout({
  children,
  breadcrumbs = [],
  navItems,
  sidebarOpen = false,
  onToggleSidebar,
  onLogout,
}: AppLayoutProps) {
  const { session } = useAuth();
  const { collapsed: sidebarCollapsed, toggleCollapsed: toggleSidebarCollapsed } =
    usePersistedCollapsed(MAIN_SIDEBAR_STORAGE_KEY);
  const grantedPermissions = session?.permissions ?? [];
  const bypass = config.devBypassEnabled;

  const resolvedNavItems = React.useMemo(() => {
    return navItems.flatMap((item) => {
      const section = mainNavigationSection(item.path);
      if (!canAccessMainNavigation(section, grantedPermissions, bypass)) return [];

      let targetPath = item.path;
      if (section === "/admin") {
        targetPath = firstAccessibleAdminPath(grantedPermissions, bypass) ?? item.path;
      } else if (section === "/data-integration") {
        targetPath = firstAccessibleDataIntegrationPath(grantedPermissions, bypass) ?? item.path;
      }

      if (targetPath === item.path) return [item];
      return [
        {
          ...item,
          path: targetPath,
          onClick: (event: React.MouseEvent) => pushInternalNavigation(targetPath, event),
        },
      ];
    });
  }, [bypass, grantedPermissions, navItems]);

  const routeAllowed = canAccessApplicationPath(
    `${window.location.pathname}${window.location.search}`,
    grantedPermissions,
    bypass,
  );

  const guardedChildren = routeAllowed ? (
    children
  ) : (
    <PageShell>
      <PageHeader title={uiLabels.permissionDeniedPageTitle} />
      <EmptyState
        title={uiLabels.permissionDeniedTitle}
        description={uiLabels.permissionDeniedDescription}
        actionLabel={uiLabels.permissionDeniedBackToDashboard}
        onAction={() => {
          if (window.location.pathname !== "/dashboard") {
            window.history.pushState(null, "", "/dashboard");
          }
          window.dispatchEvent(new PopStateEvent("popstate"));
        }}
      />
    </PageShell>
  );

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
          {resolvedNavItems.map((item) => (
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

        <main className="app-content">{guardedChildren}</main>
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
