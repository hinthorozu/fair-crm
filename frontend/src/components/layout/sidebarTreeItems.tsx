import React from "react";
import { adminLabels, DISABLED_ADMIN_NAV_ITEMS } from "../../labels/adminLabels";
import { dataIntegrationLabels, DISABLED_NAV_ITEMS } from "../../labels/dataIntegrationLabels";
import { organizationLabels } from "../../labels/organizationLabels";
import {
  canAccessAdminSection,
  canAccessDataIntegrationSection,
} from "../../permissions/navigationPermissions";
import type { GrantedPermissionCollection } from "../../permissions/corePermissions";
import { AdminNavIcon, DataIntegrationNavIcon, NavIconComingSoon } from "./NavIcons";
import type { NavChild } from "./AppLayout";

function childActive(path: string, pathname: string): boolean {
  if (path === "/data-integration/imports") {
    return pathname === path || pathname.startsWith("/data-integration/imports/continue/");
  }
  if (path === "/data-integration/imports/new") {
    return pathname === path || pathname.startsWith("/data-integration/imports/fair/");
  }
  if (path === "/data-integration/adapters") {
    return pathname === path || pathname.startsWith(`${path}/`);
  }
  if (path === "/data-integration/run-history") {
    return pathname === path || pathname.startsWith("/data-integration/runs/");
  }
  if (path === "/admin/fair-stand/items") {
    return pathname === path || pathname.startsWith(`${path}/`);
  }
  return pathname === path;
}

function linkChild(
  id: string,
  label: string,
  path: string,
  pathname: string,
  icon: React.ReactNode,
  onNavigate: (path: string, event: React.MouseEvent) => void,
): NavChild {
  return {
    key: id,
    path,
    label,
    icon,
    active: childActive(path, pathname),
    onClick: (event) => onNavigate(path, event),
  };
}

export function dataIntegrationSidebarChildren(
  pathname: string,
  granted: GrantedPermissionCollection,
  bypass: boolean,
  onNavigate: (path: string, event: React.MouseEvent) => void,
  onDisabled: (event: React.MouseEvent) => void,
): NavChild[] {
  const items = [
    { id: "imports", label: dataIntegrationLabels.navImports, path: "/data-integration/imports" },
    { id: "new", label: dataIntegrationLabels.navNewImport, path: "/data-integration/imports/new" },
    { id: "jobs", label: dataIntegrationLabels.navJobs, path: "/data-integration/jobs" },
    { id: "reports", label: dataIntegrationLabels.navReports, path: "/data-integration/reports" },
    { id: "adapters", label: dataIntegrationLabels.navAdapters, path: "/data-integration/adapters" },
    { id: "run-history", label: dataIntegrationLabels.navRunHistory, path: "/data-integration/run-history" },
    { id: "scraper-test", label: dataIntegrationLabels.navScraperTest, path: "/data-integration/scraper-test" },
  ].filter((item) => canAccessDataIntegrationSection(item.id, granted, bypass));

  const links = items.map((item) =>
    linkChild(item.id, item.label, item.path, pathname, <DataIntegrationNavIcon id={item.id} />, onNavigate),
  );
  if (links.length === 0) return [];
  return [
    ...links,
    ...DISABLED_NAV_ITEMS.map((item) => ({
      key: item.id,
      label: item.label,
      icon: <NavIconComingSoon />,
      disabled: true,
      onClick: onDisabled,
    })),
  ];
}

export function adminSidebarChildren(
  pathname: string,
  granted: GrantedPermissionCollection,
  bypass: boolean,
  onNavigate: (path: string, event: React.MouseEvent) => void,
  onDisabled: (event: React.MouseEvent) => void,
): NavChild[] {
  const canAccess = (section: string) => canAccessAdminSection(section, granted, bypass);
  const system = [
    { id: "organizations", label: organizationLabels.nav, path: "/admin/system/organizations" },
    { id: "users", label: "Kullanıcılar", path: "/admin/system/users" },
    { id: "roles", label: "Roller ve Yetkiler", path: "/admin/system/roles" },
    { id: "backups", label: adminLabels.navDatabaseBackups, path: "/admin/system/backups" },
  ].filter((item) => canAccess(item.id));
  const cost = canAccess("cost-catalog")
    ? [{ id: "cost-catalog", label: "Maliyet Kataloğu", path: "/admin/cost-catalog" }]
    : [];
  const fairStand = [
    ...(canAccess("fair-stand-settings")
      ? [{ id: "fair-stand-settings", label: "Temel Ayarlar", path: "/admin/fair-stand/settings" }]
      : []),
    ...(canAccess("fair-stand-catalog")
      ? [{ id: "fair-stand-catalog", label: "Katalog Yönetimi", path: "/admin/fair-stand/catalog" }]
      : []),
    ...(canAccess("fair-stand-previews")
      ? [{ id: "fair-stand-previews", label: "Katalog Önizlemeleri", path: "/admin/fair-stand/previews" }]
      : []),
    ...(canAccess("fair-stand-units")
      ? [{ id: "fair-stand-units", label: adminLabels.fairStandUnitsTitle, path: "/admin/fair-stand/units" }]
      : []),
    ...(canAccess("fair-stand-items")
      ? [{ id: "fair-stand-items", label: adminLabels.fairStandItemsTitle, path: "/admin/fair-stand/items" }]
      : []),
    ...(canAccess("fair-stand-item-types")
      ? [{ id: "fair-stand-item-types", label: adminLabels.fairStandItemTypesTitle, path: "/admin/fair-stand/item-types" }]
      : []),
    ...(canAccess("fair-stand-rule-types")
      ? [{ id: "fair-stand-rule-types", label: adminLabels.fairStandRuleTypesTitle, path: "/admin/fair-stand/rule-types" }]
      : []),
    ...(canAccess("fair-stand-rules")
      ? [{ id: "fair-stand-rules", label: adminLabels.fairStandRulesTitle, path: "/admin/fair-stand/rules" }]
      : []),
  ];
  const smtp = [
    { id: "email-accounts", label: adminLabels.navSmtpAccounts, path: "/admin/email-accounts" },
    { id: "mail-templates", label: adminLabels.navMailTemplates, path: "/admin/smtp-operations/templates" },
    { id: "quote-templates", label: "Teklif Şablonları", path: "/admin/smtp-operations/quote-templates" },
    { id: "template-contents", label: "Şablon İçerikleri", path: "/admin/smtp-operations/template-contents" },
    { id: "mail-operations", label: adminLabels.navMailOperations, path: "/admin/smtp-operations/mail-operations" },
  ].filter((item) => canAccess(item.id));
  const capabilities = canAccess("operation-capabilities")
    ? [{ id: "operation-capabilities", label: adminLabels.navOperationCapabilities, path: "/admin/operation-capabilities" }]
    : [];
  const toLinks = (items: { id: string; label: string; path: string }[]) =>
    items.map((item) =>
      linkChild(item.id, item.label, item.path, pathname, <AdminNavIcon id={item.id} />, onNavigate),
    );
  const disabled = DISABLED_ADMIN_NAV_ITEMS.map((item) => ({
    key: item.id,
    label: item.label,
    icon: <NavIconComingSoon />,
    disabled: true,
    onClick: onDisabled,
  }));
  const children: NavChild[] = [];
  if (system.length > 0) {
    children.push({
      key: "heading-system",
      label: adminLabels.systemTitle,
      heading: true,
      children: [...toLinks(system), ...disabled],
    });
  }
  if (cost.length > 0) {
    children.push({
      key: "heading-cost",
      label: "Maliyet",
      heading: true,
      children: toLinks(cost),
    });
  }
  if (fairStand.length > 0) {
    children.push({
      key: "heading-fair-stand",
      label: "Fair Stand",
      heading: true,
      children: toLinks(fairStand),
    });
  }
  if (smtp.length > 0) {
    children.push({
      key: "heading-smtp",
      label: adminLabels.smtpOperationsTitle,
      heading: true,
      children: toLinks(smtp),
    });
  }
  if (capabilities.length > 0) {
    children.push({
      key: "heading-capabilities",
      label: adminLabels.navOperationCapabilities,
      heading: true,
      children: toLinks(capabilities),
    });
  }
  return children;
}
