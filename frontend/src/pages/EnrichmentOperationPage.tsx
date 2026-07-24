import { createOperation } from "../api/operations";
import { CustomerEnrichmentPage } from "./CustomerEnrichmentPage";
import { dataIntegrationLabels } from "../labels/dataIntegrationLabels";
import { operationLabels } from "../labels/operationLabels";
import type { EnrichmentRunPayload } from "../types/scraper";
import { CUSTOMER_CONTACT_ENRICHMENT_ADAPTER_KEY } from "../utils/enrichmentAdapter";

interface EnrichmentOperationPageProps {
  onCreated: (operationId: string) => void;
}

/**
 * Otomasyonlar → Zenginleştirme entry.
 * Form open does NOT create an Operation.
 * "Zenginleştirmeyi Başlat" creates OperationType.ENRICHMENT + starts enrichment engine,
 * then navigates to /operations/{operation_id}.
 */
export function EnrichmentOperationPage({ onCreated }: EnrichmentOperationPageProps) {
  const startVia = async (payload: EnrichmentRunPayload) => {
    const fairIds = (payload.fair_ids ?? [])
      .map((id) => id.trim())
      .filter(Boolean);
    const created = await createOperation({
      operation_type: "enrichment",
      title: dataIntegrationLabels.enrichmentTitle,
      source_kind: fairIds.length > 0 ? "fair" : "customer",
      source_ids: fairIds,
      type_config: {
        adapter_key: CUSTOMER_CONTACT_ENRICHMENT_ADAPTER_KEY,
        requested_fields: payload.requested_fields,
        limit: payload.limit ?? null,
        include_existing_email: payload.include_existing_email ?? false,
        company_name: payload.company_name ?? null,
        company_name_match: payload.company_name_match ?? "contains",
        address_contains: payload.address_contains ?? null,
        fair_ids: fairIds,
        fair_id: fairIds.length === 1 ? fairIds[0] : null,
      },
      start_immediately: true,
    });
    return created.id;
  };

  return (
    <CustomerEnrichmentPage
      onRunStarted={onCreated}
      startVia={startVia}
      title={operationLabels.enrichmentWizardTitle}
      subtitle={operationLabels.enrichmentWizardSubtitle}
    />
  );
}
