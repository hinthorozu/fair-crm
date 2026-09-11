import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const pageSource = readFileSync(
  fileURLToPath(new URL("../pages/DataIntegrationImportsPage.tsx", import.meta.url)),
  "utf8",
);
const navigationSource = readFileSync(
  fileURLToPath(new URL("./navigationPermissions.ts", import.meta.url)),
  "utf8",
);
const appSource = readFileSync(
  fileURLToPath(new URL("../App.tsx", import.meta.url)),
  "utf8",
);

describe("Import list continue permission consistency", () => {
  it("keeps the import list readable while the continue route requires update permission", () => {
    expect(navigationSource).toContain('pathname === "/data-integration/imports"');
    expect(navigationSource).toContain("PERMISSION_IMPORTS_READ");
    expect(navigationSource).toContain('pathname.startsWith("/data-integration/imports/continue/")');
    expect(navigationSource).toContain("PERMISSION_IMPORTS_UPDATE");
  });

  it("does not expose continue navigation to read-only users", () => {
    expect(pageSource).toContain("handlers.canUpdate && showContinue(batch.status)");
    expect(pageSource).toContain(
      "const handleOpen = canUpdate ? (onContinueBatch ?? onOpenBatch) : onOpenBatch;",
    );
    expect(pageSource).toContain("handlers.onOpenBatch ? (");
  });

  it("keeps the app continue callback pointed at the update-gated route", () => {
    expect(appSource).toContain(
      '<DataIntegrationImportsPage onContinueBatch={(batchId) => goToDataIntegration(`/data-integration/imports/continue/${batchId}`)} />',
    );
  });
});
