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
  const primaryItems = [
    {
      id: "backups",
      label: adminLabels.navDatabaseBackups,
      path: "/admin/system/backups",
    },
  ];

  return (
    <div className="admin-system-layout">
      <aside className="admin-subnav">
        <p className="admin-subnav-group">{adminLabels.moduleTitle}</p>
        <h2 className="admin-subnav-title">{adminLabels.systemTitle}</h2>
        <nav>
          {primaryItems.map((item) => (
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
      </aside>
      <div className="admin-content">{children}</div>
    </div>
  );
}
