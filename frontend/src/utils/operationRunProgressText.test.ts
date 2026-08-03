import { describe, expect, it } from "vitest";
import { normalizeOperationRunProgressText } from "./operationRunProgressText";

describe("normalizeOperationRunProgressText", () => {
  it("shows processed items before total items", () => {
    expect(normalizeOperationRunProgressText("0% (429/0)")).toBe("0% (0/429)");
    expect(normalizeOperationRunProgressText("25% (100/25)")).toBe("25% (25/100)");
  });

  it("leaves unrelated text unchanged", () => {
    expect(normalizeOperationRunProgressText("Başarılı: 10")).toBe("Başarılı: 10");
  });
});
