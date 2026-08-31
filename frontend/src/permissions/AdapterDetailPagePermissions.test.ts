import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("../pages/AdapterDetailPage.tsx", import.meta.url)),
  "utf8",
);

const permissionSource = readFileSync(
  fileURLToPath(new URL("./scraperPermissions.ts", import.meta.url)),
  "utf8",
);

describe("Adapter Detail action permissions", () => {
  it("uses the backend scraper update permission for manifest editing", () => {
    expect(permissionSource).toContain(
      'SCRAPER_PERMISSION_UPDATE = "fair_crm.scraper.update"',
    );
    expect(source).toContain("const canUpdate = can(SCRAPER_PERMISSION_UPDATE)");
  });

  it("hides and fails closed adapter editing without update permission", () => {
    expect(source).toContain("if (!canUpdate || !manifest) return;");
    expect(source).toContain("if (!canUpdate) return;");
    expect(source).toContain("...(canUpdate");
    expect(source).toContain("canUpdate={canUpdate}");
  });
});
