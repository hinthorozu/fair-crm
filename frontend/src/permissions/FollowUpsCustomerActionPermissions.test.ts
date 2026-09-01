import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("../pages/FollowUpsPage.tsx", import.meta.url)),
  "utf8",
);

describe("Follow-ups customer action permission", () => {
  it("uses the canonical customer-read action helper", () => {
    expect(source).toContain(
      'import { canOpenTodoCustomerAction } from "../permissions/todoCustomerActionPermissions";',
    );
    expect(source).toContain("const canOpenCustomer = canOpenTodoCustomerAction(grantedPermissions);");
  });

  it("hides the customer-card action without customer read permission", () => {
    expect(source).toContain("canOpenCustomer && onOpenCustomer ? (");
  });
});
