import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("../components/scraper/AdapterRunLogConsole.tsx", import.meta.url)),
  "utf8",
);

const permissionSource = readFileSync(
  fileURLToPath(new URL("./scraperPermissions.ts", import.meta.url)),
  "utf8",
);

describe("Adapter Run Log Console action permissions", () => {
  it("uses the canonical scraper execute permission", () => {
    expect(permissionSource).toContain(
      'SCRAPER_PERMISSION_EXECUTE = "fair_crm.scraper.execute"',
    );
    expect(source).toContain("const canExecute = can(SCRAPER_PERMISSION_EXECUTE)");
  });

  it("hides and fails closed run and output actions without execute permission", () => {
    expect(source).toContain("if (!canExecute) return;");
    expect(source).toContain("if (!canExecute || !selectedRunId) return;");
    expect(source).toContain("{canExecute ? (");
    expect(source).toContain('event.key === "Enter" && canExecute');
  });
});
