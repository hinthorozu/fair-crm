import React from "react";
import { adminLabels, DISABLED_ADMIN_NAV_ITEMS } from "../../labels/adminLabels";

interface AdminSystemLayoutProps {
  children: React.ReactNode;
  activeSection: string;
  onNavigate: (path: string, e: React.MouseEvent) => void;
  onDisabledClick: () => void;
}

export function AdminSystemLayout({
  children,
  activeSection,
  onNavigate,
  onDisabledClick,
}: AdminSystemLayoutProps) {
  const systemItems = [
    {
      id: "backups",
      label: adminLabels.navDatabaseBackups,
      path: "/admin/system/backups",
    },
    {
      id: "smtp",
      label: adminLabels.navSmtpAccounts,
      path: "/admin/system/smtp",
    },
  ];

  const dataOperationItems = [
    {
      id: "data-operations",
      label: adminLabels.navDataOperations,
      path: "/admin/data-operations",
    },
  ];

  return (
    <div className="admin-system-layout">
      <aside className="admin-subnav">
        <p className="admin-subnav-group">{adminLabels.moduleTitle}</p>
        <h2 className="admin-subnav-title">{adminLabels.systemTitle}</h2>
        <nav>
          {systemItems.map((item) => (
            <a
              key={item.id}
              href={item.path}
              className={`admin-subnav-link ${activeSection === item.id ? "active" : ""}`}
              onClick={(e) => onNavigate(item.path, e)}
            >
              {item.label}
            </a>
          ))}
          {DISABLED_ADMIN_NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              type="button"
              className="admin-subnav-link disabled"
              onClick={onDisabledClick}
            >
              {item.label} 🚧
            </button>
          ))}
        </nav>

        <h2 className="admin-subnav-title admin-subnav-title-secondary">{adminLabels.navDataOperations}</h2>
        <nav>
          {dataOperationItems.map((item) => (
            <a
              key={item.id}
              href={item.path}
              className={`admin-subnav-link ${activeSection === item.id ? "active" : ""}`}
              onClick={(e) => onNavigate(item.path, e)}
            >
              {item.label}
            </a>
          ))}
        </nav>
      </aside>
      <div className="admin-content">{children}</div>
    </div>
  );
}
