import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const listSource = readFileSync(
  fileURLToPath(new URL("../components/ParticipationList.tsx", import.meta.url)),
  "utf8",
);
const formSource = readFileSync(
  fileURLToPath(new URL("../components/ParticipationForm.tsx", import.meta.url)),
  "utf8",
);
const navigationSource = readFileSync(
  fileURLToPath(new URL("./navigationPermissions.ts", import.meta.url)),
  "utf8",
);

describe("Participation cross-domain permission consistency", () => {
  it("keeps customer detail navigation behind customers.read", () => {
    expect(navigationSource).toContain(
      'pathname === "/customers" || pathname.startsWith("/customers/")',
    );
    expect(navigationSource).toContain("PERMISSION_CUSTOMERS_READ");
    expect(listSource).toContain("const canReadCustomers = can(CUSTOMER_READ);");
    expect(listSource).toContain(
      "onOpenCustomer: canReadCustomers ? props.onOpenCustomer : undefined",
    );
  });

  it("does not expose fair-context create selection without customers.read", () => {
    expect(formSource).toContain('if (mode === "fair" && !lockCustomer) return CUSTOMER_READ;');
    expect(listSource).toContain(
      "onCreate: canReadCustomers ? props.onCreate : undefined",
    );
  });

  it("does not expose customer-context create selection without fairs.read", () => {
    expect(navigationSource).toContain(
      'pathname === "/fairs" || pathname.startsWith("/fairs/")',
    );
    expect(navigationSource).toContain("PERMISSION_FAIRS_READ");
    expect(formSource).toContain('if (mode === "customer" && !lockFair) return FAIR_READ;');
    expect(listSource).toContain("const canSelectFair = can(FAIR_READ);");
    expect(listSource).toContain(
      "onCreate: canSelectFair ? props.onCreate : undefined",
    );
  });
});
