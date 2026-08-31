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

  it("uses the backend scraper update permission for adapter activation changes", () => {
    expect(permissionSource).toContain(
      'SCRAPER_PERMISSION_UPDATE = "fair_crm.scraper.update"',
    );
    expect(source).toContain("const canUpdate = can(SCRAPER_PERMISSION_UPDATE)");
  });

  it("hides and fails closed activate and deactivate without update permission", () => {
    expect(source).toContain("if (!canUpdate) return;");
    expect(source).toContain("{handlers.canUpdate ? (");
    expect(source).toContain("canUpdate,");
  });
});
