import React from "react";
import { getScraperManifest } from "../api/scraper";
import { ApiError } from "../api/client";
import { EnrichmentRunPanel } from "../components/scraper/EnrichmentRunPanel";
import { Card } from "../components/ui/Card";
import { LoadingState } from "../components/ui/LoadingState";
import { PageHeader } from "../components/ui/PageHeader";
import { dataIntegrationLabels } from "../labels/dataIntegrationLabels";
import { fairLabels } from "../labels/fairLabels";
import { canRunScraperActions, getGrantedScraperPermissions } from "../permissions/scraperPermissions";
import type { ScraperManifest } from "../types/scraper";
import { CUSTOMER_CONTACT_ENRICHMENT_ADAPTER_KEY } from "../utils/enrichmentAdapter";

interface CustomerEnrichmentPageProps {
  onRunStarted: (runId: string) => void;
}

/**
 * Org-wide customer contact enrichment screen under Veri Entegrasyonu.
 * Reuses EnrichmentRunPanel (optional fair/company/address filters + email include flag).
 */
export function CustomerEnrichmentPage({ onRunStarted }: CustomerEnrichmentPageProps) {
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
    getScraperManifest(CUSTOMER_CONTACT_ENRICHMENT_ADAPTER_KEY)
      .then((manifestData) => {
        if (cancelled) return;
        setManifest(manifestData);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.message : dataIntegrationLabels.enrichmentLoadError);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return <LoadingState />;
  }

  return (
    <div className="page customer-enrichment-page">
      <PageHeader
        title={dataIntegrationLabels.enrichmentTitle}
        subtitle={dataIntegrationLabels.enrichmentSubtitle}
      />

      {error ? <div className="banner error">{error}</div> : null}

      {!canRunEnrichment ? (
        <div className="banner error">{fairLabels.enrichFairPermissionDenied}</div>
      ) : (
        <Card>
          {manifest ? (
            <EnrichmentRunPanel
              adapterKey={CUSTOMER_CONTACT_ENRICHMENT_ADAPTER_KEY}
              manifest={manifest}
              onRunStarted={onRunStarted}
            />
          ) : (
            <p className="text-muted">{dataIntegrationLabels.enrichmentLoadError}</p>
          )}
        </Card>
      )}
    </div>
  );
}
