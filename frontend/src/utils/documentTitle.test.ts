import { describe, expect, it } from "vitest";
import { adminLabels } from "../labels/adminLabels";
import { dataIntegrationLabels } from "../labels/dataIntegrationLabels";
import { labels } from "../labels";
import { scraperLabels } from "../labels/scraperLabels";
import {
  DUPLICATE_OPERATION_KEY,
  formatDocumentTitle,
  resolvePageTitle,
} from "./documentTitle";

describe("formatDocumentTitle", () => {
  it("uses brand-only title when page title is empty", () => {
    expect(formatDocumentTitle(null)).toBe("FAIR CRM");
    expect(formatDocumentTitle("")).toBe("FAIR CRM");
  });

  it("prefixes page title with brand", () => {
    expect(formatDocumentTitle("Müşteriler")).toBe("FAIR CRM — Müşteriler");
  });
});

describe("resolvePageTitle", () => {
  it("resolves customers list title", () => {
    expect(resolvePageTitle({ route: "/customers" })).toBe(labels.customers);
  });

  it("resolves import jobs title", () => {
    expect(resolvePageTitle({ route: "/data-integration/imports" })).toBe(
      dataIntegrationLabels.importsTitle,
    );
  });

  it("resolves adapter management title", () => {
    expect(resolvePageTitle({ route: "/data-integration/adapters" })).toBe(
      scraperLabels.pageTitle,
    );
  });

  it("resolves duplicate groups title", () => {
    expect(
      resolvePageTitle({
        route: "/admin/data-operations/runs/:runId",
        dataOperationKey: DUPLICATE_OPERATION_KEY,
      }),
    ).toBe(adminLabels.dataOpDuplicateGroupsTitle);
  });

  it("resolves merge preparation title when group is selected", () => {
    expect(
      resolvePageTitle({
        route: "/admin/data-operations/runs/:runId",
        search: "?group=company_name:acme",
        dataOperationKey: DUPLICATE_OPERATION_KEY,
      }),
    ).toBe(adminLabels.dataOpDuplicateGroupDetailTitle);
  });

  it("resolves analyze customers without fair title", () => {
    expect(
      resolvePageTitle({
        route: "/admin/data-operations/runs/:runId",
        dataOperationKey: "analyze_customers_without_fair",
      }),
    ).toBe(adminLabels.dataOpAnalyzeResultTitle);
  });

  it("falls back to adapter key for adapter detail", () => {
    expect(
      resolvePageTitle({
        route: "/data-integration/adapters/:adapterKey",
        adapterKey: "tuyap_old",
      }),
    ).toBe("tuyap_old");
  });
});
