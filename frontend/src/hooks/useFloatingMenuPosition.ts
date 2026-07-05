import React from "react";

export interface FloatingMenuStyle {
  top: number;
  left: number;
  minWidth: number;
}

export function useFloatingMenuPosition(
  anchorRef: React.RefObject<HTMLElement | null>,
  menuRef: React.RefObject<HTMLElement | null>,
  open: boolean,
): FloatingMenuStyle {
  const [style, setStyle] = React.useState<FloatingMenuStyle>({ top: 0, left: 0, minWidth: 0 });

  const updatePosition = React.useCallback(() => {
    const anchor = anchorRef.current;
    if (!anchor) return;

    const rect = anchor.getBoundingClientRect();
    const menuHeight = menuRef.current?.offsetHeight ?? 180;
    const menuWidth = menuRef.current?.offsetWidth ?? 176;
    const gap = 4;
    const viewportPadding = 8;

    let top = rect.bottom + gap;
    const spaceBelow = window.innerHeight - rect.bottom;
    const spaceAbove = rect.top;
    if (spaceBelow < menuHeight + gap && spaceAbove > menuHeight + gap) {
      top = rect.top - menuHeight - gap;
    }

    let left = rect.left;
    if (left + menuWidth > window.innerWidth - viewportPadding) {
      left = rect.right - menuWidth;
    }
    left = Math.max(viewportPadding, Math.min(left, window.innerWidth - menuWidth - viewportPadding));

    setStyle({
      top: Math.max(viewportPadding, top),
      left,
      minWidth: rect.width,
    });
  }, [anchorRef, menuRef]);

  React.useLayoutEffect(() => {
    if (!open) return undefined;
    updatePosition();
    const frameId = window.requestAnimationFrame(updatePosition);
    window.addEventListener("scroll", updatePosition, true);
    window.addEventListener("resize", updatePosition);
    return () => {
      window.cancelAnimationFrame(frameId);
      window.removeEventListener("scroll", updatePosition, true);
      window.removeEventListener("resize", updatePosition);
    };
  }, [open, updatePosition]);

  return style;
}
