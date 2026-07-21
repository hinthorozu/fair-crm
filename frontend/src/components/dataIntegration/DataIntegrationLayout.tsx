import React from "react";
import { dataIntegrationLabels, DISABLED_NAV_ITEMS } from "../../labels/dataIntegrationLabels";
import { usePersistedCollapsed } from "../../hooks/usePersistedCollapsed";
import { SidebarCollapseButton } from "../layout/SidebarCollapseButton";
import { DataIntegrationNavIcon, NavIconComingSoon } from "../layout/NavIcons";
import { NavLink } from "../layout/NavLink";
import { uiLabels } from "../../labels/uiLabels";

interface DataIntegrationLayoutProps {
  children: React.ReactNode;
  activeSection: string;
  onNavigate: (path: string, e: React.MouseEvent) => void;
  onDisabledClick: () => void;
}

const DI_SUBNAV_STORAGE_KEY = "fair-crm.di-subnav.collapsed";

export function DataIntegrationLayout({
  children,
  activeSection,
  onNavigate,
  onDisabledClick,
}: DataIntegrationLayoutProps) {
  const { collapsed: subnavCollapsed, toggleCollapsed: toggleSubnavCollapsed } =
    usePersistedCollapsed(DI_SUBNAV_STORAGE_KEY);

  const primaryItems = [
    { id: "imports", label: dataIntegrationLabels.navImports, path: "/data-integration/imports" },
    { id: "new", label: dataIntegrationLabels.navNewImport, path: "/data-integration/imports/new" },
    { id: "jobs", label: dataIntegrationLabels.navJobs, path: "/data-integration/jobs" },
    { id: "reports", label: dataIntegrationLabels.navReports, path: "/data-integration/reports" },
    { id: "adapters", label: dataIntegrationLabels.navAdapters, path: "/data-integration/adapters" },
    { id: "run-history", label: dataIntegrationLabels.navRunHistory, path: "/data-integration/run-history" },
    { id: "scraper-test", label: dataIntegrationLabels.navScraperTest, path: "/data-integration/scraper-test" },
    { id: "enrichment", label: dataIntegrationLabels.navEnrichment, path: "/data-integration/enrichment" },
  ];

  return (
    <div className={`data-integration-layout ${subnavCollapsed ? "di-layout-collapsed" : ""}`}>
      <aside
        className={`di-subnav ${subnavCollapsed ? "di-subnav--collapsed" : ""}`}
        aria-label={dataIntegrationLabels.moduleTitle}
        aria-expanded={!subnavCollapsed}
      >
        <div className="di-subnav-header">
          {!subnavCollapsed && <h2 className="di-subnav-title">{dataIntegrationLabels.moduleTitle}</h2>}
          <SidebarCollapseButton
            collapsed={subnavCollapsed}
            onToggle={toggleSubnavCollapsed}
            className="di-subnav-collapse-btn"
            expandLabel={uiLabels.diSubnavExpand}
            collapseLabel={uiLabels.diSubnavCollapse}
          />
        </div>
        <nav className="di-subnav-links" aria-label={dataIntegrationLabels.moduleTitle}>
          {primaryItems.map((item) => (
            <NavLink
              key={item.id}
              variant="di"
              href={item.path}
              label={item.label}
              icon={<DataIntegrationNavIcon id={item.id} />}
              active={activeSection === item.id}
              collapsed={subnavCollapsed}
              onClick={(e) => onNavigate(item.path, e)}
            />
          ))}
          {DISABLED_NAV_ITEMS.map((item) => (
            <NavLink
              key={item.id}
              variant="di"
              label={item.label}
              icon={<NavIconComingSoon />}
              disabled
              collapsed={subnavCollapsed}
              onClick={onDisabledClick}
            />
          ))}
        </nav>
      </aside>
      <div className="di-content">{children}</div>
    </div>
  );
}
