import React from "react";
import { IconButton } from "../ui/IconButton";
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
    <IconButton
      variant="bordered"
      label={label}
      icon={collapsed ? <NavIconChevronRight /> : <NavIconChevronLeft />}
      onClick={onToggle}
      aria-expanded={!collapsed}
      className={className}
    />
  );
}
