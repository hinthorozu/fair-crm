import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("./FairStandCatalogAdminPage.tsx", import.meta.url)),
  "utf8",
).replace(/\r\n/g, "\n");

describe("Fair Stand catalog category integer id UX", () => {
  it("lists ID and has no catalog key field", () => {
    expect(source).toContain('header: "ID"');
    expect(source).toContain('label="Ad"');
    expect(source).toContain('label="Sıra"');
    expect(source).toContain('label="Aktif"');
    expect(source).not.toContain("Katalog anahtarı");
    expect(source).not.toContain("catalog_key");
    expect(source).not.toContain("catalogKey");
    expect(source).toContain("updateFairStandAdminCategory(categoryEditing.id");
    expect(source).toContain("createFairStandAdminCategory(payload)");
  });
});
