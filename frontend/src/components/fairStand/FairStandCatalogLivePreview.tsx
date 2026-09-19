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
}: {
  definition: PreviewDefinition | null;
  widthCm?: number;
}) {
  const hostRef = React.useRef<HTMLDivElement>(null);

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

  return <div id="preview-live" ref={hostRef} className="fair-stand-admin-live-preview" aria-label="Canlı önizleme" />;
}
