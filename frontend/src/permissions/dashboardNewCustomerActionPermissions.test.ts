import { describe, expect, it } from "vitest";
import { CUSTOMER_CREATE } from "./customerPermissions";
import { PERMISSION_CUSTOMERS_READ } from "./navigationPermissions";
import { canStartDashboardCustomerCreate } from "./dashboardNewCustomerActionPermissions";

describe("dashboard new customer action", () => {
  it("requires both customer read and create permissions", () => {
    expect(canStartDashboardCustomerCreate([])).toBe(false);
    expect(canStartDashboardCustomerCreate([PERMISSION_CUSTOMERS_READ])).toBe(false);
    expect(canStartDashboardCustomerCreate([CUSTOMER_CREATE])).toBe(false);
    expect(
      canStartDashboardCustomerCreate([PERMISSION_CUSTOMERS_READ, CUSTOMER_CREATE]),
    ).toBe(true);
  });
});
