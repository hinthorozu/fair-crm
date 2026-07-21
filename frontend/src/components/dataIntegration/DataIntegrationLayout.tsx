import React from "react";
import { dataIntegrationLabels, DISABLED_NAV_ITEMS } from "../../labels/dataIntegrationLabels";
import { usePersistedCollapsed } from "../../hooks/usePersistedCollapsed";
import { SidebarCollapseButton } from "../layout/SidebarCollapseButton";
import { DataIntegrationNavIcon } from "../layout/NavIcons";
import { withSidebarTooltip } from "../layout/SidebarTooltip";
import { uiLabels } from "../../labels/uiLabels";

export interface DataIntegrationNavItem {
  id: string;
  label: string;
  path: string;
  active: boolean;
  disabled?: boolean;
  onClick: (e: React.MouseEvent) => void;
}

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
        <nav className="di-subnav-links">
          {primaryItems.map((item) =>
            withSidebarTooltip(
              <a
                key={item.id}
                href={item.path}
                className={`di-subnav-link ${activeSection === item.id ? "active" : ""}`}
                onClick={(e) => onNavigate(item.path, e)}
              >
                <span className="di-subnav-link-icon">
                  <DataIntegrationNavIcon id={item.id} />
                </span>
                <span className="di-subnav-link-label">{item.label}</span>
              </a>,
              { label: item.label, collapsed: subnavCollapsed },
            ),
          )}
          {DISABLED_NAV_ITEMS.map((item) =>
            withSidebarTooltip(
              <button
                key={item.id}
                type="button"
                className="di-subnav-link disabled"
                onClick={onDisabledClick}
              >
                <span className="di-subnav-link-icon" aria-hidden>
                  🚧
                </span>
                <span className="di-subnav-link-label">
                  {item.label} {!subnavCollapsed && "🚧"}
                </span>
              </button>,
              { label: item.label, collapsed: subnavCollapsed },
            ),
          )}
        </nav>
      </aside>
      <div className="di-content">{children}</div>
    </div>
  );
}
