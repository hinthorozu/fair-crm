import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("../pages/CustomersPage.tsx", import.meta.url)),
  "utf8",
);
const permissionSource = readFileSync(
  fileURLToPath(new URL("./customerPermissions.ts", import.meta.url)),
  "utf8",
);

describe("Customers page delete permission", () => {
  it("uses canonical customers delete permission", () => {
    expect(permissionSource).toContain('CUSTOMER_DELETE = "fair_crm.customers.delete"');
    expect(source).toContain("const canDelete = can(CUSTOMER_DELETE)");
  });

  it("fails closed for archive and restore handlers", () => {
    expect(source.match(/if \(!canDelete\) return;/g)?.length ?? 0).toBeGreaterThanOrEqual(2);
    expect(source).toContain("onArchive={");
    expect(source).toContain("onRestore={");
  });
});
