import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const wrapperSource = readFileSync(
  fileURLToPath(new URL("../pages/ScraperRunHistoryPage.tsx", import.meta.url)),
  "utf8",
);
const legacySource = readFileSync(
  fileURLToPath(new URL("../pages/ScraperRunHistoryPageLegacy.tsx", import.meta.url)),
  "utf8",
);
const navigationSource = readFileSync(
  fileURLToPath(new URL("./navigationPermissions.ts", import.meta.url)),
  "utf8",
);

describe("Scraper run-history import continue permission consistency", () => {
  it("keeps run history readable independently of import continuation", () => {
    expect(navigationSource).toContain('pathname === "/data-integration/run-history"');
    expect(navigationSource).toContain("PERMISSION_SCRAPER_READ");
  });

  it("keeps the import continue route gated by imports read plus update", () => {
    expect(navigationSource).toContain('pathname.startsWith("/data-integration/imports/continue/")');
    expect(navigationSource).toContain("PERMISSION_IMPORTS_READ");
    expect(navigationSource).toContain("PERMISSION_IMPORTS_UPDATE");
  });

  it("removes the run-history import callback unless both import permissions are granted", () => {
    expect(wrapperSource).toContain(
      "can(PERMISSION_IMPORTS_READ) && can(PERMISSION_IMPORTS_UPDATE)",
    );
    expect(wrapperSource).toContain(
      "onOpenImportBatch={canContinueImport ? props.onOpenImportBatch : undefined}",
    );
    expect(legacySource).toContain("run.import_batch_id && handlers.onOpenImportBatch");
  });
});
