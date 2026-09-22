import React from "react";
import { renderCatalogPreview } from "@fair-stand/catalogPreviewRenderer.js";

type PreviewDefinition = {
  id: number;
  markup: string;
  cssCode: string;
};

export function FairStandCatalogLivePreview({
  definition,
  widthCm = 100,
  id,
  className,
}: {
  definition: PreviewDefinition | null;
  widthCm?: number;
  id?: string;
  className?: string;
}) {
  const autoId = React.useId();
  const hostRef = React.useRef<HTMLDivElement>(null);
  const hostId = id ?? `preview-live-${autoId}`;

  React.useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    host.replaceChildren();
    if (!definition || !definition.markup) return;
    try {
      const node = renderCatalogPreview(
        {
          id: definition.id || 0,
          markup: definition.markup,
          cssCode: definition.cssCode,
        },
        { widthCm, eyeCount: 2, videoWallRows: 2, videoWallCols: 2 },
        document,
      );
      host.appendChild(node);
    } catch {
      const error = document.createElement("p");
      error.className = "text-muted";
      error.textContent = "Önizleme geçersiz tanım nedeniyle gösterilemedi.";
      host.appendChild(error);
    }
  }, [definition, widthCm]);

  return (
    <div
      id={hostId}
      ref={hostRef}
      className={["fair-stand-admin-live-preview", className].filter(Boolean).join(" ")}
      aria-label="Canlı önizleme"
    />
  );
}
