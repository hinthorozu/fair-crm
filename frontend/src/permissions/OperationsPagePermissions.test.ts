import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("../pages/OperationsPage.tsx", import.meta.url)),
  "utf8",
);

const navigationPermissionSource = readFileSync(
  fileURLToPath(new URL("./navigationPermissions.ts", import.meta.url)),
  "utf8",
);

const operationPermissionSource = readFileSync(
  fileURLToPath(new URL("./operationPermissions.ts", import.meta.url)),
  "utf8",
);

describe("Operations action permissions", () => {
  it("uses the canonical operations create permission for the new action", () => {
    expect(navigationPermissionSource).toContain(
      'PERMISSION_OPERATIONS_CREATE = "fair_crm.operations.create"',
    );
  });

  it("hides and fails closed the new operation entry point without create permission", () => {
    expect(source).toContain("const canCreate = can(PERMISSION_OPERATIONS_CREATE)");
    expect(source).toContain("canCreate ? (");
    expect(source).toContain("open={canCreate && typeModalOpen}");
    expect(source).toContain("if (!canCreate) return;");
  });

  it("uses the backend operations execute permission for operation mutations", () => {
    expect(operationPermissionSource).toContain(
      'OPERATION_EXECUTE = "fair_crm.operations.execute"',
    );
    expect(source).toContain("const canExecute = can(OPERATION_EXECUTE)");
  });

  it("hides and fails closed the start action without execute permission", () => {
    expect(source).toContain("if (!canExecute) return;");
    expect(source).toContain(
      'canExecute && ["draft", "ready", "active"].includes(item.status) && !latestRunActive',
    );
  });

  it("hides and fails closed the cancel action without execute permission", () => {
    expect(source.match(/if \(!canExecute\) return;/g)).toHaveLength(2);
    expect(source).toContain(
      'canExecute && ["draft", "ready", "active"].includes(item.status) ? (',
    );
  });
});
