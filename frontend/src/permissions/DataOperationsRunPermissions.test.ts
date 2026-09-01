import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  new URL("../pages/DataOperationsPage.tsx", import.meta.url),
  "utf8",
);

describe("DataOperationsPage run permissions", () => {
  it("requires operation create and execute permissions for runs", () => {
    expect(source).toContain(
      "const canRun = can(PERMISSION_OPERATIONS_CREATE) && can(OPERATION_EXECUTE);",
    );
  });

  it("fails closed before creating an immediately started operation", () => {
    expect(source).toContain("if (!canRun) return;");
    expect(source).toContain("start_immediately: true");
  });

  it("hides the run affordance without both permissions", () => {
    expect(source).toContain("{canRun ? (");
    expect(source).toContain("onClick={() => void handleRun(operation)}");
  });
});
