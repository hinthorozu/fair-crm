import { describe, expect, it } from "vitest";
import { CUSTOMER_READ } from "./customerPermissions";
import { canOpenDashboardCustomerLink } from "./dashboardCustomerLinkPermissions";

describe("dashboard customer link permissions", () => {
  it("requires customers.read before offering customer navigation", () => {
    expect(canOpenDashboardCustomerLink([])).toBe(false);
    expect(canOpenDashboardCustomerLink([CUSTOMER_READ])).toBe(true);
  });
});
