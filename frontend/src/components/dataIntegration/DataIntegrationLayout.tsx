import React from "react";
import { dataIntegrationLabels, DISABLED_NAV_ITEMS } from "../../labels/dataIntegrationLabels";

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

export function DataIntegrationLayout({
  children,
  activeSection,
  onNavigate,
  onDisabledClick,
}: DataIntegrationLayoutProps) {
  const primaryItems = [
    { id: "imports", label: dataIntegrationLabels.navImports, path: "/data-integration/imports" },
    { id: "new", label: dataIntegrationLabels.navNewImport, path: "/data-integration/imports/new" },
    { id: "jobs", label: dataIntegrationLabels.navJobs, path: "/data-integration/jobs" },
    { id: "reports", label: dataIntegrationLabels.navReports, path: "/data-integration/reports" },
  ];

  return (
    <div className="data-integration-layout">
      <aside className="di-subnav">
        <h2 className="di-subnav-title">{dataIntegrationLabels.moduleTitle}</h2>
        <nav>
          {primaryItems.map((item) => (
            <a
              key={item.id}
              href={item.path}
              className={`di-subnav-link ${activeSection === item.id ? "active" : ""}`}
              onClick={(e) => onNavigate(item.path, e)}
            >
              {item.label}
            </a>
          ))}
          {DISABLED_NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              type="button"
              className="di-subnav-link disabled"
              onClick={onDisabledClick}
            >
              {item.label} 🚧
            </button>
          ))}
        </nav>
      </aside>
      <div className="di-content">{children}</div>
    </div>
  );
}
