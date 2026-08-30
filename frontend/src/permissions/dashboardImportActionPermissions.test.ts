import { describe, expect, it } from "vitest";
import {
  canStartDashboardImport,
  DASHBOARD_IMPORT_CREATE,
} from "./dashboardImportActionPermissions";

describe("dashboard import action permissions", () => {
  it("requires imports.create before offering import start navigation", () => {
    expect(canStartDashboardImport([])).toBe(false);
    expect(canStartDashboardImport([DASHBOARD_IMPORT_CREATE])).toBe(true);
  });
});
