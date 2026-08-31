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

describe("Scraper run history download permission", () => {
  it("uses canonical scraper execute permission", () => {
    expect(permissionSource).toContain('SCRAPER_PERMISSION_EXECUTE = "fair_crm.scraper.execute"');
    expect(source).toContain("const canExecute = can(SCRAPER_PERMISSION_EXECUTE)");
  });

  it("hides and fails closed downloads without execute permission", () => {
    expect(source).toContain("if (!canExecute) return;");
    expect(source).toContain("canDownload: canExecute");
    expect(source).toContain("handlers.canDownload ? (");
  });
});
