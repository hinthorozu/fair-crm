import { describe, expect, it } from "vitest";
import { normalizeSourceText } from "./normalizeSourceText";

describe("normalizeSourceText", () => {
  it("converts CRLF to LF without changing tokens or indentation", () => {
    const crlf = "const handleCreate = async (values: TodoFormValues) => {\r\n    if (!canCreate) return;";
    const lf = "const handleCreate = async (values: TodoFormValues) => {\n    if (!canCreate) return;";
    expect(normalizeSourceText(crlf)).toBe(lf);
    expect(normalizeSourceText(lf)).toBe(lf);
    expect(normalizeSourceText(crlf)).toContain("if (!canCreate) return;");
  });
});
