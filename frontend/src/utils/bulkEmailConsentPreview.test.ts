import { describe, expect, it } from "vitest";
import type { BulkEmailOperationPreviewRecipient } from "../types/bulkEmailOperation";
import { operationLabels } from "../labels/operationLabels";

function skipReasonLabel(reason: string | null): string {
  switch (reason) {
    case "customer_email_consent":
      return operationLabels.bulkEmailSkipReasonCustomerConsent;
    case "contact_email_consent":
      return operationLabels.bulkEmailSkipReasonContactConsent;
    case "duplicate_email":
      return operationLabels.bulkEmailSkipReasonDuplicate;
    default:
      return reason ?? "—";
  }
}

function filterByStatus(
  recipients: BulkEmailOperationPreviewRecipient[],
  status: "" | "will_send" | "skip",
): BulkEmailOperationPreviewRecipient[] {
  return recipients.filter((item) => {
    if (status === "will_send" && item.status !== "will_send") return false;
    if (status === "skip" && item.status !== "skip") return false;
    return true;
  });
}

describe("bulk email preview consent skip display", () => {
  const rows: BulkEmailOperationPreviewRecipient[] = [
    {
      recipient_key: "1",
      email: "ok@example.com",
      source: "customer",
      status: "will_send",
      skip_reason: null,
      recipient_name: "OK",
      company_name: "OK Co",
      fair_id: "fair-1",
      fair_name: "Food İst",
      customer_id: "c1",
      contact_id: null,
      participation_id: "p1",
    },
    {
      recipient_key: "2",
      email: "blocked-customer@example.com",
      source: "customer",
      status: "skip",
      skip_reason: "customer_email_consent",
      recipient_name: "Blocked Customer",
      company_name: "Blocked Co",
      fair_id: "fair-1",
      fair_name: "Food İst",
      customer_id: "c2",
      contact_id: null,
      participation_id: "p2",
    },
    {
      recipient_key: "3",
      email: "blocked-contact@example.com",
      source: "contact",
      status: "skip",
      skip_reason: "contact_email_consent",
      recipient_name: "Blocked Contact",
      company_name: "OK Co",
      fair_id: "fair-1",
      fair_name: "Food İst",
      customer_id: "c1",
      contact_id: "ct1",
      participation_id: "p1",
    },
  ];

  it("maps consent skip reasons to Atlanacak labels", () => {
    expect(skipReasonLabel("customer_email_consent")).toBe("Customer e-posta iletişim izni kapalı");
    expect(skipReasonLabel("contact_email_consent")).toBe("Contact e-posta iletişim izni kapalı");
  });

  it("includes consent rows in Atlanacak status filter totals", () => {
    const skipped = filterByStatus(rows, "skip");
    expect(skipped).toHaveLength(2);
    expect(skipped.map((row) => row.skip_reason)).toEqual([
      "customer_email_consent",
      "contact_email_consent",
    ]);
    expect(filterByStatus(rows, "will_send")).toHaveLength(1);
    expect(filterByStatus(rows, "")).toHaveLength(3);
  });
});
