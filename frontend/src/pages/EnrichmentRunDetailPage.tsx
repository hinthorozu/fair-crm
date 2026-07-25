import React from "react";
import { EnrichmentRunDetailPanel } from "../components/scraper/EnrichmentRunDetailPanel";
import { PageHeader } from "../components/ui/PageHeader";
import { Card } from "../components/ui/Card";
import { scraperLabels } from "../labels/scraperLabels";
import { PageShell } from "../components/ui/PageShell";

interface EnrichmentRunDetailPageProps {
  runId: string;
  adapterKey?: string;
  onBack: () => void;
  onOpenImportBatch?: (batchId: string) => void;
}

/**
 * Legacy DI route: /data-integration/runs/:runId
 * Body is shared with Operation Detail via EnrichmentRunDetailPanel.
 */
export function EnrichmentRunDetailPage({
  runId,
  adapterKey,
  onBack,
  onOpenImportBatch,
}: EnrichmentRunDetailPageProps) {
  return (
    <PageShell className="enrichment-run-detail-page">
      <PageHeader
        title={scraperLabels.enrichmentRunDetailTitle}
        subtitle={scraperLabels.enrichmentRunDetailSubtitle}
        actions={
          <button type="button" className="btn secondary" onClick={onBack}>
            {scraperLabels.enrichmentRunDetailBackHistory}
          </button>
        }
      />

      <Card>
        <EnrichmentRunDetailPanel
          runId={runId}
          adapterKey={adapterKey}
          onOpenImportBatch={onOpenImportBatch}
          showActions
        />
      </Card>
    </PageShell>
  );
}
