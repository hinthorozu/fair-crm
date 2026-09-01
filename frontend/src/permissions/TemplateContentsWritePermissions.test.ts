import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("../pages/TemplateContentsPage.tsx", import.meta.url)),
  "utf8",
);

describe("Template Contents write permissions", () => {
  it("selects create or update permission for tag and content save", () => {
    expect(source).toContain("const canSaveTag = editingTag ? canUpdate : canCreate;");
    expect(source).toContain("const canSaveContent = editingContent ? canUpdate : canCreate;");
    expect(source).toContain("if (!canSaveTag || !tagName.trim()) return;");
    expect(source).toContain("if (!canSaveContent) return;");
  });

  it("fails closed before tag and content delete mutations", () => {
    expect(source.match(/if \(!canDelete\) return;/g)?.length).toBeGreaterThanOrEqual(2);
  });

  it("hides modal save actions without the matching write capability", () => {
    expect(source).toContain("{canSaveTag ? <button type=\"submit\" className=\"btn primary\"");
    expect(source).toContain("{canSaveContent ? <button type=\"submit\" className=\"btn primary\"");
  });
});
