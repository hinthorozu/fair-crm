import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("../pages/ScraperRunHistoryPage.tsx", import.meta.url)),
  "utf8",
);
const permissionSource = readFileSync(
  fileURLToPath(new URL("./scraperPermissions.ts", import.meta.url)),
  "utf8",
);

describe("Scraper run history delete permission", () => {
  it("uses canonical scraper delete permission", () => {
    expect(permissionSource).toContain('SCRAPER_PERMISSION_DELETE = "fair_crm.scraper.delete"');
    expect(source).toContain("const canDelete = can(SCRAPER_PERMISSION_DELETE)");
  });

  it("hides and fails closed delete without delete permission", () => {
    expect(source).toContain("if (!canDelete || !runToDelete) return;");
    expect(source).toContain("handlers.canDelete ? (");
    expect(source).toContain("canDelete && runToDelete ? (");
  });
});
