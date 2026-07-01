import React from "react";

export interface TabItem<T extends string> {
  id: T;
  label: string;
  badge?: number;
}

interface TabsProps<T extends string> {
  items: TabItem<T>[];
  active: T;
  onChange: (id: T) => void;
  ariaLabel?: string;
}

export function Tabs<T extends string>({
  items,
  active,
  onChange,
  ariaLabel = "Sekmeler",
}: TabsProps<T>) {
  return (
    <div className="tabs" role="tablist" aria-label={ariaLabel}>
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          role="tab"
          id={`tab-${item.id}`}
          aria-selected={active === item.id}
          aria-controls={`panel-${item.id}`}
          className={active === item.id ? "tab active" : "tab"}
          onClick={() => onChange(item.id)}
        >
          {item.label}
          {item.badge !== undefined && item.badge > 0 && (
            <span className="tab-badge">{item.badge}</span>
          )}
        </button>
      ))}
    </div>
  );
}

interface TabPanelProps {
  id: string;
  labelledBy: string;
  active: boolean;
  children: React.ReactNode;
}

export function TabPanel({ id, labelledBy, active, children }: TabPanelProps) {
  if (!active) return null;
  return (
    <div
      id={id}
      role="tabpanel"
      aria-labelledby={labelledBy}
      className="tab-panel"
    >
      {children}
    </div>
  );
}
