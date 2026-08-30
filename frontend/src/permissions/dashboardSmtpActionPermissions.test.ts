import { describe, expect, it } from "vitest";
import { PERMISSION_EMAIL_ACCOUNTS_READ } from "./navigationPermissions";
import { canOpenDashboardSmtpSettings } from "./dashboardSmtpActionPermissions";

describe("dashboard smtp action", () => {
  it("checks email account read permission", () => {
    expect(canOpenDashboardSmtpSettings([])).toBe(false);
    expect(canOpenDashboardSmtpSettings([PERMISSION_EMAIL_ACCOUNTS_READ])).toBe(true);
  });
});
