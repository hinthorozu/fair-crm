import { describe, expect, it } from "vitest";
import {
  clearIdIfMatches,
  shouldApplyAccountScopedResult,
} from "./emailAccountAsyncIsolation";

describe("shouldApplyAccountScopedResult", () => {
  const base = {
    requestId: 3,
    activeRequestId: 3,
    operationAccountId: "A",
    activeOperationAccountId: "A",
    modalAccountId: "A",
  };

  it("applies when request and modal still target the same account", () => {
    expect(shouldApplyAccountScopedResult(base)).toBe(true);
  });

  it("ignores stale request after a newer request started", () => {
    expect(
      shouldApplyAccountScopedResult({
        ...base,
        requestId: 2,
        activeRequestId: 3,
      }),
    ).toBe(false);
  });

  it("ignores result when modal switched to another account", () => {
    expect(
      shouldApplyAccountScopedResult({
        ...base,
        modalAccountId: "B",
      }),
    ).toBe(false);
  });

  it("ignores result when modal closed", () => {
    expect(
      shouldApplyAccountScopedResult({
        ...base,
        modalAccountId: null,
      }),
    ).toBe(false);
  });

  it("ignores result when active operation target was reset/invalidated", () => {
    expect(
      shouldApplyAccountScopedResult({
        ...base,
        activeOperationAccountId: null,
      }),
    ).toBe(false);
  });

  it("ignores cross-account operation id mismatch", () => {
    expect(
      shouldApplyAccountScopedResult({
        ...base,
        operationAccountId: "A",
        activeOperationAccountId: "B",
        modalAccountId: "B",
      }),
    ).toBe(false);
  });
});

describe("clearIdIfMatches", () => {
  it("clears only the finished account loading id", () => {
    expect(clearIdIfMatches("A", "A")).toBeNull();
    expect(clearIdIfMatches("B", "A")).toBe("B");
    expect(clearIdIfMatches(null, "A")).toBeNull();
  });
});

describe("email account async isolation scenarios", () => {
  it("A test → close modal → B open: A response must not apply to B", () => {
    // A started request 1, then modal closed (invalidate), then B opened with clean state.
    expect(
      shouldApplyAccountScopedResult({
        requestId: 1,
        activeRequestId: 2,
        operationAccountId: "A",
        activeOperationAccountId: null,
        modalAccountId: "B",
      }),
    ).toBe(false);
  });

  it("A pending → B open → A response ignored", () => {
    expect(
      shouldApplyAccountScopedResult({
        requestId: 1,
        activeRequestId: 2,
        operationAccountId: "A",
        activeOperationAccountId: "B",
        modalAccountId: "B",
      }),
    ).toBe(false);
  });

  it("same account reopened uses a fresh generation so old result is dropped", () => {
    expect(
      shouldApplyAccountScopedResult({
        requestId: 1,
        activeRequestId: 3,
        operationAccountId: "A",
        activeOperationAccountId: "A",
        modalAccountId: "A",
      }),
    ).toBe(false);
  });
});
