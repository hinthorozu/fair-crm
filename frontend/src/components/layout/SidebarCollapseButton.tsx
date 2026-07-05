import React from "react";
import { NavIconChevronLeft, NavIconChevronRight } from "./NavIcons";
import { uiLabels } from "../../labels/uiLabels";

interface SidebarCollapseButtonProps {
  collapsed: boolean;
  onToggle: () => void;
  className?: string;
  expandLabel?: string;
  collapseLabel?: string;
}

export function SidebarCollapseButton({
  collapsed,
  onToggle,
  className,
  expandLabel = uiLabels.sidebarExpand,
  collapseLabel = uiLabels.sidebarCollapse,
}: SidebarCollapseButtonProps) {
  const label = collapsed ? expandLabel : collapseLabel;
  return (
    <button
      type="button"
      className={`sidebar-collapse-btn ${className ?? ""}`.trim()}
      onClick={onToggle}
      aria-label={label}
      aria-expanded={!collapsed}
      title={label}
    >
      {collapsed ? <NavIconChevronRight /> : <NavIconChevronLeft />}
    </button>
  );
}
