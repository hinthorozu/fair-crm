import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("../components/scraper/EnrichmentRunDetailPanel.tsx", import.meta.url)),
  "utf8",
);
const permissionSource = readFileSync(
  fileURLToPath(new URL("./scraperPermissions.ts", import.meta.url)),
  "utf8",
);

describe("Enrichment run cancel permission", () => {
  it("uses canonical scraper execute permission", () => {
    expect(permissionSource).toContain('SCRAPER_PERMISSION_EXECUTE = "fair_crm.scraper.execute"');
    expect(source).toContain("const canExecute = can(SCRAPER_PERMISSION_EXECUTE)");
  });

  it("hides and fails closed cancel without execute permission", () => {
    expect(source).toContain("if (!canExecute) return;");
    expect(source).toContain('showActions && canExecute && run?.status === "running"');
  });
});
