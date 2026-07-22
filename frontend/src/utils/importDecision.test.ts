import { describe, expect, it } from "vitest";
import { isImportDecisionBusy } from "./importDecision";

describe("isImportDecisionBusy", () => {
  it("is idle when no decision operation is running", () => {
    expect(isImportDecisionBusy(false, false, false)).toBe(false);
  });

  it("locks the decision list while apply, bulk-assign, or wizard loading is active", () => {
    expect(isImportDecisionBusy(true, false, false)).toBe(true);
    expect(isImportDecisionBusy(false, true, false)).toBe(true);
    expect(isImportDecisionBusy(false, false, true)).toBe(true);
    expect(isImportDecisionBusy(true, true, true)).toBe(true);
  });
});
