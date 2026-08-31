import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("../pages/AdapterManagementPage.tsx", import.meta.url)),
  "utf8",
);

const permissionSource = readFileSync(
  fileURLToPath(new URL("./scraperPermissions.ts", import.meta.url)),
  "utf8",
);

describe("Adapter Management action permissions", () => {
  it("uses the backend scraper create permission for adapter creation", () => {
    expect(permissionSource).toContain(
      'SCRAPER_PERMISSION_CREATE = "fair_crm.scraper.create"',
    );
    expect(source).toContain("const canCreate = can(SCRAPER_PERMISSION_CREATE)");
  });

  it("hides and fails closed the create adapter action without create permission", () => {
    expect(source).toContain("if (!canCreate) return;");
    expect(source).toContain("{canCreate ? (");
    expect(source).toContain("{canCreate && showCreateModal ? (");
  });
});
