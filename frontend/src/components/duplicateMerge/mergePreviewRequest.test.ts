import { describe, expect, it } from "vitest";
import type { DuplicateGroupCustomerDetail } from "../../types/dataOperations";
import { buildMergePreviewRequest } from "./mergePreviewRequest";
import { commSelectionKey, createDefaultMergeSelectionState } from "./mergeSelectionState";

function customer(id: string): DuplicateGroupCustomerDetail {
  return {
    id,
    company_name: `Company ${id}`,
    legal_name: null,
    trade_name: null,
    phone: null,
    email: null,
    website: null,
    phones: [],
    emails: [
      {
        id: `${id}-email`,
        email: "shared@example.com",
        is_primary: true,
        created_at: "2026-01-01T00:00:00Z",
      },
    ],
    websites: [],
    city: null,
    country: null,
    status: "active",
    created_at: "2026-01-01T00:00:00Z",
    participations: [],
  };
}

describe("buildMergePreviewRequest", () => {
  it("maps UI selections to API payload", () => {
    const customers = [customer("a"), customer("b")];
    const state = createDefaultMergeSelectionState(customers, "a");
    state.communicationSelections.add(commSelectionKey("b", "b-email"));

    const payload = buildMergePreviewRequest("run-1", state, customers);

    expect(payload.run_id).toBe("run-1");
    expect(payload.surviving_customer_id).toBe("a");
    expect(payload.scalar_selections.company_name).toBe("a");
    expect(payload.selected_email_ids).toEqual(["a-email", "b-email"]);
    expect(payload.selected_phone_ids).toEqual([]);
    expect(payload.selected_website_ids).toEqual([]);
  });

  it("drops stale communication ids not present in current group customers", () => {
    const customers = [
      {
        ...customer("a"),
        websites: [
          {
            id: "a-website",
            website: "https://a.example.com",
            is_primary: true,
            created_at: "2026-01-01T00:00:00Z",
          },
        ],
      },
    ];
    const state = createDefaultMergeSelectionState(customers, "a");
    state.communicationSelections.add(commSelectionKey("b", "b-email"));
    state.communicationSelections.add(commSelectionKey("a", "stale-website-id"));

    const payload = buildMergePreviewRequest("run-1", state, customers);

    expect(payload.selected_email_ids).toEqual(["a-email"]);
    expect(payload.selected_phone_ids).toEqual([]);
    expect(payload.selected_website_ids).toEqual(["a-website"]);
    expect(payload.selected_website_ids).not.toContain("stale-website-id");
  });
});
