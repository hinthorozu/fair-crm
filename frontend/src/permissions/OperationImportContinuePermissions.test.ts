import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const operationDetailSource = readFileSync(
  fileURLToPath(new URL("../pages/OperationDetailPage.tsx", import.meta.url)),
  "utf8",
);
const enrichmentPanelSource = readFileSync(
  fileURLToPath(new URL("../components/scraper/EnrichmentRunDetailPanel.tsx", import.meta.url)),
  "utf8",
);
const navigationSource = readFileSync(
  fileURLToPath(new URL("./navigationPermissions.ts", import.meta.url)),
  "utf8",
);

describe("Operation-linked import continue permission consistency", () => {
  it("keeps the import continue route gated by read plus update", () => {
    expect(navigationSource).toContain('pathname.startsWith("/data-integration/imports/continue/")');
    expect(navigationSource).toContain("PERMISSION_IMPORTS_READ");
    expect(navigationSource).toContain("PERMISSION_IMPORTS_UPDATE");
  });

  it("removes the operation-detail import callback unless both permissions are granted", () => {
    expect(operationDetailSource).toContain(
      "can(PERMISSION_IMPORTS_READ) && can(PERMISSION_IMPORTS_UPDATE)",
    );
    expect(operationDetailSource).toContain(
      "onOpenImportBatch={canContinueImport ? props.onOpenImportBatch : undefined}",
    );
  });

  it("does not expose the shared enrichment import link without both permissions", () => {
    expect(enrichmentPanelSource).toContain(
      "can(PERMISSION_IMPORTS_READ) && can(PERMISSION_IMPORTS_UPDATE)",
    );
    expect(enrichmentPanelSource).toContain(
      "summary?.import_batch_id && canContinueImport",
    );
  });
});
