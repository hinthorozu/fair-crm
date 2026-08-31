import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("../pages/CustomersPage.tsx", import.meta.url)),
  "utf8",
);

describe("Customers page update permission", () => {
  it("uses canonical customers update permission", () => {
    expect(source).toContain("const canUpdate = can(CUSTOMER_UPDATE)");
  });

  it("fails closed before updating a customer", () => {
    expect(source).toContain("const handleUpdate = async (values: CreateCustomerPayload) => {\n    if (!canUpdate) return;");
  });
});
