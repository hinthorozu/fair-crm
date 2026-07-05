import React from "react";
import { adminLabels, DISABLED_ADMIN_NAV_ITEMS } from "../../labels/adminLabels";
import { uiLabels } from "../../labels/uiLabels";
import { usePersistedCollapsed } from "../../hooks/usePersistedCollapsed";
import { AdminNavIcon } from "../layout/NavIcons";
import { SidebarCollapseButton } from "../layout/SidebarCollapseButton";
import { withSidebarTooltip } from "../layout/SidebarTooltip";

interface AdminSystemLayoutProps {
  children: React.ReactNode;
  activeSection: string;
  onNavigate: (path: string, e: React.MouseEvent) => void;
  onDisabledClick: () => void;
}

const ADMIN_SUBNAV_STORAGE_KEY = "fair-crm.admin-subnav.collapsed";

export function AdminSystemLayout({
  children,
  activeSection,
  onNavigate,
  onDisabledClick,
}: AdminSystemLayoutProps) {
  const { collapsed: subnavCollapsed, toggleCollapsed: toggleSubnavCollapsed } =
    usePersistedCollapsed(ADMIN_SUBNAV_STORAGE_KEY);

  const systemItems = [
    {
      id: "backups",
      label: adminLabels.navDatabaseBackups,
      path: "/admin/system/backups",
    },
  ];

  const smtpOperationsItems = [
    {
      id: "smtp",
      label: adminLabels.navSmtpAccounts,
      path: "/admin/smtp-operations/accounts",
    },
    {
      id: "mail-templates",
      label: adminLabels.navMailTemplates,
      path: "/admin/smtp-operations/templates",
    },
    {
      id: "mail-operations",
      label: adminLabels.navMailOperations,
      path: "/admin/smtp-operations/mail-operations",
    },
  ];

  const dataOperationItems = [
    {
      id: "data-operations",
      label: adminLabels.navDataOperations,
      path: "/admin/data-operations",
    },
  ];

  const renderNavLink = (item: { id: string; label: string; path: string }) =>
    withSidebarTooltip(
      <a
        key={item.id}
        href={item.path}
        className={`admin-subnav-link ${activeSection === item.id ? "active" : ""}`}
        onClick={(e) => onNavigate(item.path, e)}
      >
        <span className="admin-subnav-link-icon">
          <AdminNavIcon id={item.id} />
        </span>
        <span className="admin-subnav-link-label">{item.label}</span>
      </a>,
      { label: item.label, collapsed: subnavCollapsed },
    );

  const renderDisabledLink = (item: { id: string; label: string }) =>
    withSidebarTooltip(
      <button
        key={item.id}
        type="button"
        className="admin-subnav-link disabled"
        onClick={onDisabledClick}
      >
        <span className="admin-subnav-link-icon" aria-hidden>
          🚧
        </span>
        <span className="admin-subnav-link-label">
          {item.label} {!subnavCollapsed && "🚧"}
        </span>
      </button>,
      { label: item.label, collapsed: subnavCollapsed },
    );

  const renderSectionTitle = (title: string, first = false) =>
    !subnavCollapsed ? (
      <h2
        className={
          first ? "admin-subnav-title" : "admin-subnav-title admin-subnav-title-secondary"
        }
      >
        {title}
      </h2>
    ) : null;

  return (
    <div className={`admin-system-layout ${subnavCollapsed ? "admin-layout-collapsed" : ""}`}>
      <aside
        className={`admin-subnav ${subnavCollapsed ? "admin-subnav--collapsed" : ""}`}
        aria-label={adminLabels.moduleTitle}
        aria-expanded={!subnavCollapsed}
      >
        <div className="admin-subnav-header">
          {!subnavCollapsed ? (
            <div>
              <p className="admin-subnav-group">{adminLabels.moduleTitle}</p>
            </div>
          ) : null}
          <SidebarCollapseButton
            collapsed={subnavCollapsed}
            onToggle={toggleSubnavCollapsed}
            className="admin-subnav-collapse-btn"
            expandLabel={uiLabels.diSubnavExpand}
            collapseLabel={uiLabels.diSubnavCollapse}
          />
        </div>

        {renderSectionTitle(adminLabels.systemTitle, true)}
        <nav className="admin-subnav-links" aria-label={adminLabels.systemTitle}>
          {systemItems.map(renderNavLink)}
          {DISABLED_ADMIN_NAV_ITEMS.map(renderDisabledLink)}
        </nav>

        {renderSectionTitle(adminLabels.smtpOperationsTitle)}
        <nav className="admin-subnav-links" aria-label={adminLabels.smtpOperationsTitle}>
          {smtpOperationsItems.map(renderNavLink)}
        </nav>

        {renderSectionTitle(adminLabels.navDataOperations)}
        <nav className="admin-subnav-links" aria-label={adminLabels.navDataOperations}>
          {dataOperationItems.map(renderNavLink)}
        </nav>
      </aside>
      <div className="admin-content">{children}</div>
    </div>
  );
}
