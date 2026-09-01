import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("../pages/QuoteTemplatesPage.tsx", import.meta.url)),
  "utf8",
);

describe("Quote Templates write permissions", () => {
  it("selects create or update permission for template save", () => {
    expect(source).toContain("const canSaveTemplate = editing ? canUpdate : canCreate;");
    expect(source).toContain("if (!canSaveTemplate) return;");
  });

  it("uses create-or-update permission for logo upload", () => {
    expect(source).toContain("const canUploadLogo = canCreate || canUpdate;");
    expect(source).toContain("if (!canUploadLogo || !file) return;");
    expect(source).toContain("disabled={uploading || !canUploadLogo}");
  });

  it("hides the modal save action without the matching write capability", () => {
    expect(source).toContain("{canSaveTemplate ? <button type=\"submit\" className=\"btn primary\"");
  });
});
