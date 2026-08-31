import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const runPanelSource = readFileSync(
  fileURLToPath(new URL("../components/scraper/EnrichmentRunPanel.tsx", import.meta.url)),
  "utf8",
);

const resetPanelSource = readFileSync(
  fileURLToPath(new URL("../components/scraper/EnrichmentStateResetPanel.tsx", import.meta.url)),
  "utf8",
);

const permissionSource = readFileSync(
  fileURLToPath(new URL("./scraperPermissions.ts", import.meta.url)),
  "utf8",
);

describe("Enrichment execute permissions", () => {
  it("uses the canonical scraper execute permission", () => {
    expect(permissionSource).toContain(
      'SCRAPER_PERMISSION_EXECUTE = "fair_crm.scraper.execute"',
    );
    expect(runPanelSource).toContain("const canExecute = can(SCRAPER_PERMISSION_EXECUTE)");
    expect(resetPanelSource).toContain("const canExecute = can(SCRAPER_PERMISSION_EXECUTE)");
  });

  it("hides and fails closed enrichment run actions without execute permission", () => {
    expect(runPanelSource).toContain("if (!canExecute) return;");
    expect(runPanelSource).toContain("{canExecute ? (");
  });

  it("hides and fails closed enrichment state reset without execute permission", () => {
    expect(resetPanelSource).toContain("if (!canExecute) return;");
    expect(resetPanelSource).toContain("if (!canExecute) return null;");
  });
});
