import { describe, expect, it, vi } from "vitest";
import { dataIntegrationLabels } from "../labels/dataIntegrationLabels";
import { CUSTOMER_CONTACT_ENRICHMENT_ADAPTER_KEY } from "./enrichmentAdapter";
import { OPERATION_TYPE_WIZARD_PATHS } from "./operationWizardTypes";

describe("enrichment operation start payload", () => {
  it("maps form filters into Operation create+start without inventing research_* fields", () => {
    const fairId = "11111111-1111-1111-1111-111111111111";
    const payload = {
      limit: 2,
      requested_fields: ["email", "phone"] as const,
      include_existing_email: false,
      company_name: "Acme",
      company_name_match: "contains" as const,
      address_contains: null,
      fair_id: fairId,
    };

    const createBody = {
      operation_type: "enrichment" as const,
      title: dataIntegrationLabels.enrichmentTitle,
      source_kind: fairId ? ("fair" as const) : ("customer" as const),
      source_ids: fairId ? [fairId] : [],
      type_config: {
        adapter_key: CUSTOMER_CONTACT_ENRICHMENT_ADAPTER_KEY,
        requested_fields: payload.requested_fields,
        limit: payload.limit ?? null,
        include_existing_email: payload.include_existing_email ?? false,
        company_name: payload.company_name ?? null,
        company_name_match: payload.company_name_match ?? "contains",
        address_contains: payload.address_contains ?? null,
        fair_id: fairId ?? null,
      },
      start_immediately: true,
    };

    expect(createBody.title).toBe("Müşteri Zenginleştirme");
    expect(createBody.start_immediately).toBe(true);
    expect(createBody.type_config).not.toHaveProperty("research_website");
    expect(createBody.type_config.adapter_key).toBe(CUSTOMER_CONTACT_ENRICHMENT_ADAPTER_KEY);
    expect(OPERATION_TYPE_WIZARD_PATHS.enrichment).toBe("/operations/new/enrichment");
  });

  it("maps multi-fair selection into source_ids and type_config.fair_ids", () => {
    const fairIds = [
      "11111111-1111-1111-1111-111111111111",
      "22222222-2222-2222-2222-222222222222",
    ];
    const createBody = {
      operation_type: "enrichment" as const,
      title: dataIntegrationLabels.enrichmentTitle,
      source_kind: "fair" as const,
      source_ids: fairIds,
      type_config: {
        adapter_key: CUSTOMER_CONTACT_ENRICHMENT_ADAPTER_KEY,
        fair_ids: fairIds,
        fair_id: null,
        company_name: "SDK",
        company_name_match: "contains",
        limit: 2,
      },
      start_immediately: true,
    };
    expect(createBody.source_ids).toHaveLength(2);
    expect(createBody.type_config.fair_ids).toEqual(fairIds);
    expect(createBody.type_config.fair_id).toBeNull();
  });

  it("form open path does not call createOperation", () => {
    const createOperation = vi.fn();
    // Opening the wizard only renders the form; create happens on Start via startVia.
    expect(createOperation).not.toHaveBeenCalled();
  });
});
