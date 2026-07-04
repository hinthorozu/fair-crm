import React from "react";
import type { AdapterFeature } from "../../types/scraper";
import { FEATURE_SHORT_LABELS } from "../../labels/scraperLabels";

interface AdapterFeatureBadgesProps {
  features: AdapterFeature[];
}

export function AdapterFeatureBadges({ features }: AdapterFeatureBadgesProps) {
  if (!features.length) return <>—</>;

  return (
    <div className="adapter-feature-badges">
      {features.map((feature) => {
        const shortLabel = FEATURE_SHORT_LABELS[feature.key] ?? feature.label;
        return (
          <span
            key={feature.key}
            className={feature.enabled ? "adapter-feature-badge enabled" : "adapter-feature-badge disabled"}
            title={feature.label}
          >
            {shortLabel}
          </span>
        );
      })}
    </div>
  );
}
