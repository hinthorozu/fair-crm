import React from "react";

export type ViewportTier = "mobile" | "tablet" | "laptop";

/**
 * ADR-032 viewport tiers:
 * mobile &lt; 768, tablet 768–1023, laptop ≥ 1024
 */
export function useViewportTier(): ViewportTier {
  const getTier = React.useCallback((): ViewportTier => {
    if (typeof window === "undefined") return "laptop";
    const width = window.innerWidth;
    if (width < 768) return "mobile";
    if (width < 1024) return "tablet";
    return "laptop";
  }, []);

  const [tier, setTier] = React.useState<ViewportTier>(getTier);

  React.useEffect(() => {
    const onResize = () => setTier(getTier());
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [getTier]);

  return tier;
}
