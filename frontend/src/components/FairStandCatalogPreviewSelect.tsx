import React from "react";
import { createPortal } from "react-dom";
import type { FairStandAdminPreview } from "../api/fairStandAdmin";
import { useFloatingMenuPosition } from "../hooks/useFloatingMenuPosition";
import { adminLabels } from "../labels/adminLabels";
import { FairStandCatalogLivePreview } from "./fairStand/FairStandCatalogLivePreview";

export interface FairStandCatalogPreviewSelectProps {
  id?: string;
  value: string;
  previews: FairStandAdminPreview[];
  disabled?: boolean;
  onChange: (previewId: string) => void;
}

export function FairStandCatalogPreviewSelect({
  id,
  value,
  previews,
  disabled = false,
  onChange,
}: FairStandCatalogPreviewSelectProps) {
  const [open, setOpen] = React.useState(false);
  const containerRef = React.useRef<HTMLDivElement>(null);
  const dropdownRef = React.useRef<HTMLDivElement>(null);
  const menuStyle = useFloatingMenuPosition(containerRef, dropdownRef, open);

  const selectedId = value.trim() ? Number(value) : null;
  const selected =
    selectedId != null && Number.isFinite(selectedId)
      ? (previews.find((preview) => preview.id === selectedId) ?? null)
      : null;

  const options = React.useMemo(() => {
    return previews
      .filter((preview) => preview.isActive || preview.id === selectedId)
      .slice()
      .sort((a, b) => a.sortIndex - b.sortIndex || a.id - b.id);
  }, [previews, selectedId]);

  React.useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: MouseEvent) => {
      const target = event.target as Node;
      if (containerRef.current?.contains(target)) return;
      if (dropdownRef.current?.contains(target)) return;
      setOpen(false);
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  const selectOption = (nextValue: string) => {
    onChange(nextValue);
    setOpen(false);
  };

  const dropdown =
    open && typeof document !== "undefined"
      ? createPortal(
          <div
            ref={dropdownRef}
            className="fair-stand-preview-select-dropdown floating-dropdown-menu"
            role="listbox"
            style={{
              top: menuStyle.top,
              left: menuStyle.left,
              width: menuStyle.minWidth || undefined,
              minWidth: menuStyle.minWidth || undefined,
            }}
          >
            <button
              type="button"
              role="option"
              className="fair-stand-preview-select-option"
              aria-selected={!selected}
              onClick={() => selectOption("")}
            >
              <span className="fair-stand-preview-select-option-label">
                {adminLabels.fairStandCatalogNone}
              </span>
            </button>
            {options.map((preview) => {
              const isSelected = preview.id === selectedId;
              return (
                <button
                  key={preview.id}
                  type="button"
                  role="option"
                  className={[
                    "fair-stand-preview-select-option",
                    isSelected ? "selected" : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  aria-selected={isSelected}
                  onClick={() => selectOption(String(preview.id))}
                >
                  <span className="fair-stand-preview-select-thumb" aria-hidden="true">
                    <FairStandCatalogLivePreview definition={preview} widthCm={60} />
                  </span>
                  <span className="fair-stand-preview-select-option-text">
                    <span className="fair-stand-preview-select-option-label">
                      {preview.displayName}
                    </span>
                    {!preview.isActive ? (
                      <span className="fair-stand-preview-select-option-meta">
                        {adminLabels.fairStandPreviewsStatusInactive}
                      </span>
                    ) : null}
                  </span>
                </button>
              );
            })}
            {options.length === 0 ? (
              <div className="fair-stand-preview-select-message">
                {adminLabels.fairStandPreviewsEmptyTitle}
              </div>
            ) : null}
          </div>,
          document.body,
        )
      : null;

  return (
    <div className="fair-stand-preview-select" ref={containerRef}>
      <button
        type="button"
        id={id}
        className="fair-stand-preview-select-trigger"
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => {
          if (!disabled) setOpen((prev) => !prev);
        }}
      >
        {selected ? (
          <span className="fair-stand-preview-select-trigger-content">
            <span className="fair-stand-preview-select-thumb" aria-hidden="true">
              <FairStandCatalogLivePreview definition={selected} widthCm={60} />
            </span>
            <span className="fair-stand-preview-select-trigger-label">{selected.displayName}</span>
          </span>
        ) : (
          <span className="fair-stand-preview-select-placeholder">
            {adminLabels.fairStandCatalogSelectPlaceholder}
          </span>
        )}
      </button>
      {dropdown}
    </div>
  );
}
