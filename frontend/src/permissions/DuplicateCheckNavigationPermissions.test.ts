import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const operationsPageSource = readFileSync(
  fileURLToPath(new URL("../pages/OperationsPage.tsx", import.meta.url)),
  "utf8",
);
const shortcutSource = readFileSync(
  fileURLToPath(new URL("../utils/duplicateCheckOperation.ts", import.meta.url)),
  "utf8",
);
const navigationSource = readFileSync(
  fileURLToPath(new URL("./navigationPermissions.ts", import.meta.url)),
  "utf8",
);

describe("Duplicate-check navigation permission consistency", () => {
  it("keeps the duplicate-check wizard aligned with its route permission set", () => {
    expect(navigationSource).toContain('pathname === "/operations/new/duplicate-check"');
    expect(navigationSource).toContain("OPERATION_EXECUTE");
    expect(navigationSource).toContain("PERMISSION_DATA_OPERATIONS_READ");
    expect(operationsPageSource).toContain(
      "const canCreateDuplicateCheckOperation = canExecute && canReadDataOperations;",
    );
    expect(operationsPageSource).toContain(
      'if (type === "duplicate_check") return canCreateDuplicateCheckOperation;',
    );
  });

  it("does not use the stronger duplicate-result route without data-operation read permission", () => {
    expect(shortcutSource).toContain(
      "!getGrantedCorePermissions().has(PERMISSION_DATA_OPERATIONS_READ)",
    );
    expect(shortcutSource).toContain("return null;");
  });

  it("still permits the New Operation entry when duplicate-check is the only allowed wizard", () => {
    expect(operationsPageSource).toContain("canCreateDuplicateCheckOperation;");
  });
});
