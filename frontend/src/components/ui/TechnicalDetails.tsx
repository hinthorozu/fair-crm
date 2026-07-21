import React from "react";
import { uiLabels } from "../../labels/uiLabels";

export interface TechnicalDetailItem {
  label: string;
  value: React.ReactNode;
}

export interface TechnicalDetailsProps {
  items: TechnicalDetailItem[];
  defaultOpen?: boolean;
  className?: string;
  title?: string;
}

/** Collapsible technical field block (run_id, UUID, URL, keys) — ADR-032. */
export function TechnicalDetails({
  items,
  defaultOpen = false,
  className = "",
  title = uiLabels.technicalDetails,
}: TechnicalDetailsProps) {
  const [open, setOpen] = React.useState(defaultOpen);
  const visible = items.filter((item) => item.value != null && item.value !== "");

  if (visible.length === 0) return null;

  return (
    <div className={`technical-details ${className}`.trim()}>
      <button
        type="button"
        className="btn link technical-details-toggle"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
      >
        {open ? "− " : "+ "}
        {title}
      </button>
      {open ? (
        <div className="technical-details-list">
          {visible.map((item) => (
            <div key={item.label} className="table-child-field table-child-field--technical">
              <span className="table-child-field-label">{item.label}</span>
              <div className="table-child-field-value text-mono text-wrap">{item.value}</div>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
