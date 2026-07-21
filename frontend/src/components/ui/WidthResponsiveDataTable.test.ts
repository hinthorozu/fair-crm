import { describe, expect, it } from "vitest";
import { resolveVisibleColumnCount } from "./WidthResponsiveDataTable";

describe("resolveVisibleColumnCount", () => {
  it("keeps all columns when they fit without expand", () => {
    expect(resolveVisibleColumnCount([100, 100, 100], 300, 40)).toBe(3);
  });

  it("hides trailing columns and reserves expand width", () => {
    // 100+100+100=300 > 250 → need expand; budget 210 → first two fit
    expect(resolveVisibleColumnCount([100, 100, 100], 250, 40)).toBe(2);
  });

  it("keeps at least one column in very narrow containers", () => {
    expect(resolveVisibleColumnCount([120, 120, 120], 50, 40)).toBe(1);
  });

  it("hides from the end (column order = priority)", () => {
    const visible = resolveVisibleColumnCount(
      [160, 90, 100, 90, 120, 160, 140, 140, 140],
      480,
      44,
    );
    expect(visible).toBeGreaterThanOrEqual(1);
    expect(visible).toBeLessThan(9);
  });

  it("reserves expand when forceExpandReserve is set (detail-only columns)", () => {
    // Columns fit exactly, but detail-only forces expand reserve → may hide trailing
    expect(resolveVisibleColumnCount([100, 100, 100], 300, 40, { forceExpandReserve: true })).toBe(2);
  });
});
