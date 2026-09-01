import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("../pages/TodoDetailPage.tsx", import.meta.url)),
  "utf8",
);

describe("Todo detail customer link permission", () => {
  it("uses the canonical customer navigation helper", () => {
    expect(source).toContain(
      "const canOpenCustomer = canOpenTodoCustomerAction(grantedPermissions)",
    );
  });

  it("gates the metadata customer link with customers read permission", () => {
    expect(source).toContain(
      "{canOpenCustomer && todo.customer_id && customerName && onOpenCustomer ? (",
    );
  });
});
