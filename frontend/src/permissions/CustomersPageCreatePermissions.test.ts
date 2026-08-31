import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("../pages/CustomersPage.tsx", import.meta.url)),
  "utf8",
);

describe("Customers page create permission", () => {
  it("uses canonical customers create permission", () => {
    expect(source).toContain("const canCreate = can(CUSTOMER_CREATE)");
  });

  it("fails closed for both create handlers", () => {
    expect(source).toContain("const handleCreate = async (values: CreateCustomerPayload) => {\n    if (!canCreate) return;");
    expect(source).toContain("const handleCreateAndNew = async (values: CreateCustomerPayload) => {\n    if (!canCreate) return;");
  });
});
