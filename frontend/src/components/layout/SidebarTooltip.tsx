import React from "react";
import { createPortal } from "react-dom";

interface SidebarTooltipProps {
  label: string;
  collapsed: boolean;
  children: React.ReactElement;
}

function useSidebarTooltip(collapsed: boolean, label: string) {
  const ref = React.useRef<HTMLElement>(null);
  const [visible, setVisible] = React.useState(false);
  const [position, setPosition] = React.useState({ top: 0, left: 0 });

  const updatePosition = React.useCallback(() => {
    const element = ref.current;
    if (!element) return;
    const rect = element.getBoundingClientRect();
    setPosition({
      top: rect.top + rect.height / 2,
      left: rect.right + 10,
    });
  }, []);

  const showTooltip = React.useCallback(() => {
    if (!collapsed || !label) return;
    updatePosition();
    setVisible(true);
  }, [collapsed, label, updatePosition]);

  const hideTooltip = React.useCallback(() => {
    setVisible(false);
  }, []);

  React.useEffect(() => {
    if (!visible) return;
    const onScrollOrResize = () => updatePosition();
    window.addEventListener("scroll", onScrollOrResize, true);
    window.addEventListener("resize", onScrollOrResize);
    return () => {
      window.removeEventListener("scroll", onScrollOrResize, true);
      window.removeEventListener("resize", onScrollOrResize);
    };
  }, [visible, updatePosition]);

  const floatingTooltip =
    visible && collapsed && label
      ? createPortal(
          <div
            className="sidebar-floating-tooltip"
            style={{ top: position.top, left: position.left }}
            role="tooltip"
          >
            {label}
          </div>,
          document.body,
        )
      : null;

  return { ref, showTooltip, hideTooltip, floatingTooltip };
}

function bindTooltipHandlers(
  element: React.ReactElement,
  handlers: {
    ref: React.Ref<HTMLElement>;
    showTooltip: () => void;
    hideTooltip: () => void;
  },
): React.ReactElement {
  const { ref, showTooltip, hideTooltip } = handlers;
  const existingRef = (element as React.ReactElement & { ref?: React.Ref<HTMLElement> }).ref;

  return React.cloneElement(element, {
    ref: (node: HTMLElement | null) => {
      (handlers.ref as React.MutableRefObject<HTMLElement | null>).current = node;
      if (typeof existingRef === "function") existingRef(node);
      else if (existingRef && typeof existingRef === "object") {
        (existingRef as React.MutableRefObject<HTMLElement | null>).current = node;
      }
    },
    onMouseEnter: (event: React.MouseEvent<HTMLElement>) => {
      showTooltip();
      element.props.onMouseEnter?.(event);
    },
    onMouseLeave: (event: React.MouseEvent<HTMLElement>) => {
      hideTooltip();
      element.props.onMouseLeave?.(event);
    },
    onFocus: (event: React.FocusEvent<HTMLElement>) => {
      showTooltip();
      element.props.onFocus?.(event);
    },
    onBlur: (event: React.FocusEvent<HTMLElement>) => {
      hideTooltip();
      element.props.onBlur?.(event);
    },
  });
}

/** Attach a floating tooltip to a sidebar nav item when collapsed. */
export function withSidebarTooltip(
  element: React.ReactElement,
  { label, collapsed }: SidebarTooltipProps,
): React.ReactElement {
  if (!collapsed) return element;
  return <SidebarTooltipItem label={label} collapsed={collapsed} element={element} />;
}

function SidebarTooltipItem({
  label,
  collapsed,
  element,
}: SidebarTooltipProps & { element: React.ReactElement }) {
  const tooltip = useSidebarTooltip(collapsed, label);
  return (
    <>
      {bindTooltipHandlers(element, tooltip)}
      {tooltip.floatingTooltip}
    </>
  );
}

export function SidebarTooltipTarget({ label, collapsed, children }: SidebarTooltipProps) {
  return withSidebarTooltip(children, { label, collapsed });
}
