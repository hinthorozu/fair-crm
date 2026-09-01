import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("../pages/QuoteEditorPage.tsx", import.meta.url)),
  "utf8",
);

describe("Quote Editor save permission", () => {
  it("selects create or update permission from quote existence", () => {
    expect(source).toContain(
      "const canSaveQuote = existing ? permissions.has(QUOTE_UPDATE) : permissions.has(QUOTE_CREATE);",
    );
  });

  it("fails closed before quote mutation", () => {
    expect(source).toContain('if (!canSaveQuote) { setError("Teklifi kaydetme yetkiniz yok."); return; }');
  });

  it("hides the save action when quote write permission is missing", () => {
    expect(source).toContain("{canSaveQuote ? <button type=\"button\" className=\"btn primary\"");
  });
});
