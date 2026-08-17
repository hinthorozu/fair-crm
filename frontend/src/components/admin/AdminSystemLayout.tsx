import React from "react";
import { useAuth } from "../../auth/AuthContext";
import { config } from "../../config";
import { adminLabels, DISABLED_ADMIN_NAV_ITEMS } from "../../labels/adminLabels";
import { organizationLabels } from "../../labels/organizationLabels";
import { uiLabels } from "../../labels/uiLabels";
import { canAccessAdminSection } from "../../permissions/navigationPermissions";
import { usePersistedCollapsed } from "../../hooks/usePersistedCollapsed";
import { UsersAdminPage } from "../../pages/UsersAdminPage";
import { RoleManagementPage } from "../../pages/RoleManagementPage";
import { CostCatalogPage } from "../../pages/CostCatalogPage";
import { AdminNavIcon, NavIconComingSoon } from "../layout/NavIcons";
import { NavLink } from "../layout/NavLink";
import { SidebarCollapseButton } from "../layout/SidebarCollapseButton";

interface AdminSystemLayoutProps { children: React.ReactNode; activeSection: string; onNavigate: (path: string, e: React.MouseEvent) => void; onDisabledClick: () => void; }
const ADMIN_SUBNAV_STORAGE_KEY = "fair-crm.admin-subnav.collapsed";

export function AdminSystemLayout({ children, activeSection, onNavigate, onDisabledClick }: AdminSystemLayoutProps) {
  const { session } = useAuth();
  const { collapsed: subnavCollapsed, toggleCollapsed: toggleSubnavCollapsed } = usePersistedCollapsed(ADMIN_SUBNAV_STORAGE_KEY);
  const grantedPermissions = session?.permissions ?? [];
  const bypass = config.devBypassEnabled;
  const canAccess = React.useCallback(
    (section: string) => canAccessAdminSection(section, grantedPermissions, bypass),
    [bypass, grantedPermissions],
  );
  const pathname = window.location.pathname.replace(/\/$/, "");
  const usersRouteActive = pathname === "/admin/system/users";
  const rolesRouteActive = pathname === "/admin/system/roles";
  const costCatalogRouteActive = pathname === "/admin/cost-catalog";
  const resolvedActiveSection = usersRouteActive ? "users" : rolesRouteActive ? "roles" : costCatalogRouteActive ? "cost-catalog" : activeSection;
  const resolvedChildren = usersRouteActive ? <UsersAdminPage /> : rolesRouteActive ? <RoleManagementPage /> : costCatalogRouteActive ? <CostCatalogPage /> : children;

  const systemItems = [
    { id: "organizations", label: organizationLabels.nav, path: "/admin/system/organizations" },
    { id: "users", label: "Kullanıcılar", path: "/admin/system/users" },
    { id: "roles", label: "Roller ve Yetkiler", path: "/admin/system/roles" },
    { id: "backups", label: adminLabels.navDatabaseBackups, path: "/admin/system/backups" },
  ].filter((item) => canAccess(item.id));
  const costItems = canAccess("cost-catalog") ? [{ id: "cost-catalog", label: "Maliyet Kataloğu", path: "/admin/cost-catalog" }] : [];
  const smtpOperationsItems = [
    { id: "email-accounts", label: adminLabels.navSmtpAccounts, path: "/admin/email-accounts" },
    { id: "mail-templates", label: adminLabels.navMailTemplates, path: "/admin/smtp-operations/templates" },
    { id: "quote-templates", label: "Teklif Şablonları", path: "/admin/smtp-operations/quote-templates" },
    { id: "template-contents", label: "Şablon İçerikleri", path: "/admin/smtp-operations/template-contents" },
    { id: "mail-operations", label: adminLabels.navMailOperations, path: "/admin/smtp-operations/mail-operations" },
  ].filter((item) => canAccess(item.id));
  const operationCapabilityItems = canAccess("operation-capabilities")
    ? [{ id: "operation-capabilities", label: adminLabels.navOperationCapabilities, path: "/admin/operation-capabilities" }]
    : [];
  const renderSectionTitle = (title: string, first = false) => !subnavCollapsed ? <h2 className={first ? "admin-subnav-title" : "admin-subnav-title admin-subnav-title-secondary"}>{title}</h2> : null;
  const renderItems = (items: { id: string; label: string; path: string }[]) => items.map((item) => <NavLink key={item.id} variant="admin" href={item.path} label={item.label} icon={<AdminNavIcon id={item.id} />} active={resolvedActiveSection === item.id} collapsed={subnavCollapsed} onClick={(e) => onNavigate(item.path, e)} />);
  const hasSystemSection = systemItems.length > 0;

  return <div className={`admin-system-layout ${subnavCollapsed ? "admin-layout-collapsed" : ""}`}>
    <aside className={`admin-subnav ${subnavCollapsed ? "admin-subnav--collapsed" : ""}`} aria-label={adminLabels.moduleTitle} aria-expanded={!subnavCollapsed}>
      <div className="admin-subnav-header">{!subnavCollapsed ? <div><p className="admin-subnav-group">{adminLabels.moduleTitle}</p></div> : null}<SidebarCollapseButton collapsed={subnavCollapsed} onToggle={toggleSubnavCollapsed} className="admin-subnav-collapse-btn" expandLabel={uiLabels.diSubnavExpand} collapseLabel={uiLabels.diSubnavCollapse} /></div>
      {hasSystemSection ? <>{renderSectionTitle(adminLabels.systemTitle, true)}<nav className="admin-subnav-links" aria-label={adminLabels.systemTitle}>{renderItems(systemItems)}{DISABLED_ADMIN_NAV_ITEMS.map((item) => <NavLink key={item.id} variant="admin" label={item.label} icon={<NavIconComingSoon />} disabled collapsed={subnavCollapsed} onClick={onDisabledClick} />)}</nav></> : null}
      {costItems.length ? <>{renderSectionTitle("Maliyet", !hasSystemSection)}<nav className="admin-subnav-links" aria-label="Maliyet">{renderItems(costItems)}</nav></> : null}
      {smtpOperationsItems.length ? <>{renderSectionTitle(adminLabels.smtpOperationsTitle, !hasSystemSection && !costItems.length)}<nav className="admin-subnav-links" aria-label={adminLabels.smtpOperationsTitle}>{renderItems(smtpOperationsItems)}</nav></> : null}
      {operationCapabilityItems.length ? <>{renderSectionTitle(adminLabels.navOperationCapabilities, !hasSystemSection && !costItems.length && !smtpOperationsItems.length)}<nav className="admin-subnav-links" aria-label={adminLabels.navOperationCapabilities}>{renderItems(operationCapabilityItems)}</nav></> : null}
    </aside>
    <div className="admin-content">{resolvedChildren}</div>
  </div>;
}
