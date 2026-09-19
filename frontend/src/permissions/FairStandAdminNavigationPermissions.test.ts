import { describe, expect, it } from "vitest";
import {
  canAccessAdminSection,
  canAccessApplicationPath,
} from "./navigationPermissions";
import {
  FAIR_STAND_CATALOG_READ,
  FAIR_STAND_PREVIEWS_READ,
} from "./fairStandAdminPermissions";

describe("Fair Stand admin navigation", () => {
  it("shows catalog and preview admin only with SYSTEM Fair Stand permissions", () => {
    const granted = [FAIR_STAND_CATALOG_READ, FAIR_STAND_PREVIEWS_READ];
    expect(canAccessAdminSection("fair-stand-catalog", granted)).toBe(true);
    expect(canAccessAdminSection("fair-stand-previews", granted)).toBe(true);
    expect(canAccessApplicationPath("/admin/fair-stand/catalog", granted)).toBe(true);
    expect(canAccessApplicationPath("/admin/fair-stand/previews", granted)).toBe(true);
  });

  it("hides Fair Stand admin from organization catalog readers", () => {
    const granted = ["fair_crm.cost_catalog.categories.read"];
    expect(canAccessAdminSection("fair-stand-catalog", granted)).toBe(false);
    expect(canAccessAdminSection("fair-stand-previews", granted)).toBe(false);
    expect(canAccessApplicationPath("/admin/fair-stand/catalog", granted)).toBe(false);
    expect(canAccessApplicationPath("/admin/fair-stand/previews", granted)).toBe(false);
  });
});
