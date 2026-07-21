import React from "react";
import { getFair } from "../api/fairs";
import { getScraperManifest } from "../api/scraper";
import { ApiError } from "../api/client";
import { EnrichmentRunPanel } from "../components/scraper/EnrichmentRunPanel";
import { Card } from "../components/ui/Card";
import { LoadingState } from "../components/ui/LoadingState";
import { PageHeader, type PageHeaderAction } from "../components/ui/PageHeader";
import { fairLabels } from "../labels/fairLabels";
import { canRunScraperActions, getGrantedScraperPermissions } from "../permissions/scraperPermissions";
import type { Fair } from "../types/fair";
import type { ScraperManifest } from "../types/scraper";
import { CUSTOMER_CONTACT_ENRICHMENT_ADAPTER_KEY } from "../utils/enrichmentAdapter";
import { Banner } from "../components/ui/Banner";
import { PageShell } from "../components/ui/PageShell";

interface FairEnrichmentRunPageProps {
  fairId: string;
  onBack: () => void;
  onRunStarted: (runId: string) => void;
  onFairLoaded?: (name: string) => void;
}

/**
 * Dedicated, fair-scoped enrichment run screen — reuses the same `EnrichmentRunPanel`
 * form and Run Detail routing as the org-wide enrichment flow, so a manually started
 * fair-scoped run behaves identically from the user's point of view once it's underway.
 * Deliberately not a modal: matches the full-page layout used elsewhere for run screens.
 */
export function FairEnrichmentRunPage({
  fairId,
  onBack,
  onRunStarted,
  onFairLoaded,
}: FairEnrichmentRunPageProps) {
  const [fair, setFair] = React.useState<Fair | null>(null);
  const [manifest, setManifest] = React.useState<ScraperManifest | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const canRunEnrichment = React.useMemo(
    () => canRunScraperActions(getGrantedScraperPermissions()),
    [],
  );

  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all([getFair(fairId), getScraperManifest(CUSTOMER_CONTACT_ENRICHMENT_ADAPTER_KEY)])
      .then(([fairData, manifestData]) => {
        if (cancelled) return;
        setFair(fairData);
        setManifest(manifestData);
        onFairLoaded?.(fairData.name);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.message : fairLabels.enrichFairModalLoadError);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [fairId, onFairLoaded]);

  if (loading) {
    return <LoadingState />;
  }

  const headerActions: PageHeaderAction[] = [
    {
      id: "back",
      label: fairLabels.enrichFairBackToFair,
      variant: "secondary",
      onClick: onBack,
    },
  ];

  return (
    <PageShell className="fair-enrichment-run-page">
      <PageHeader
        title={fairLabels.enrichFairModalTitle}
        subtitle={fair ? fair.name : undefined}
        actions={headerActions}
      />

      {error ? <Banner variant="error">{error}</Banner> : null}

      {!canRunEnrichment ? (
        <Banner variant="error">{fairLabels.enrichFairPermissionDenied}</Banner>
      ) : (
        <Card>
          {manifest ? (
            <EnrichmentRunPanel
              adapterKey={CUSTOMER_CONTACT_ENRICHMENT_ADAPTER_KEY}
              manifest={manifest}
              fairId={fairId}
              onRunStarted={onRunStarted}
            />
          ) : (
            <p className="text-muted">{fairLabels.enrichFairModalLoadError}</p>
          )}
        </Card>
      )}
    </PageShell>
  );
}
