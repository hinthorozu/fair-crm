import { describe, expect, it } from "vitest";
import {
  canStartDashboardImport,
  DASHBOARD_IMPORT_CREATE,
  DASHBOARD_IMPORT_FAIRS_READ,
} from "./dashboardImportActionPermissions";

describe("dashboard import action permissions", () => {
  it("requires import create plus fair discovery before offering general import navigation", () => {
    expect(canStartDashboardImport([])).toBe(false);
    expect(canStartDashboardImport([DASHBOARD_IMPORT_CREATE])).toBe(false);
    expect(canStartDashboardImport([DASHBOARD_IMPORT_FAIRS_READ])).toBe(false);
    expect(
      canStartDashboardImport([DASHBOARD_IMPORT_CREATE, DASHBOARD_IMPORT_FAIRS_READ]),
    ).toBe(true);
  });
});
