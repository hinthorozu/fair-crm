import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const linkedFairsSource = readFileSync(
  fileURLToPath(new URL("../components/scraper/AdapterLinkedFairsTab.tsx", import.meta.url)),
  "utf8",
);
const enrichmentSource = readFileSync(
  fileURLToPath(new URL("../components/scraper/EnrichmentRunPanel.tsx", import.meta.url)),
  "utf8",
);
const navigationSource = readFileSync(
  fileURLToPath(new URL("./navigationPermissions.ts", import.meta.url)),
  "utf8",
);

describe("Adapter detail cross-domain navigation permissions", () => {
  it("keeps fair detail behind fairs read", () => {
    expect(navigationSource).toContain(
      'pathname === "/fairs" || pathname.startsWith("/fairs/")',
    );
    expect(navigationSource).toContain("PERMISSION_FAIRS_READ");
    expect(linkedFairsSource).toContain("const canOpenFair = can(FAIR_READ);");
    expect(linkedFairsSource).toContain(
      "buildColumns(canOpenFair ? onOpenFair : undefined)",
    );
    expect(linkedFairsSource).toContain("fair.id && onOpenFair ? (");
  });

  it("keeps import continuation behind imports read plus update", () => {
    expect(navigationSource).toContain(
      'pathname.startsWith("/data-integration/imports/continue/")',
    );
    expect(navigationSource).toContain("PERMISSION_IMPORTS_READ");
    expect(navigationSource).toContain("PERMISSION_IMPORTS_UPDATE");
    expect(enrichmentSource).toContain(
      "can(PERMISSION_IMPORTS_READ) && can(PERMISSION_IMPORTS_UPDATE)",
    );
    expect(enrichmentSource).toContain(
      "summary.import_batch_id && canContinueImport",
    );
  });
});
