import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("../pages/OperationsPage.tsx", import.meta.url)),
  "utf8",
);

const modalSource = readFileSync(
  fileURLToPath(new URL("../components/operations/NewOperationTypeModal.tsx", import.meta.url)),
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

  it("allows Bulk Email execute to open and select its new-operation entry", () => {
    expect(source).toContain("const canCreate = can(PERMISSION_OPERATIONS_CREATE)");
    expect(source).toContain(
      "const canOpenNewOperation = canCreate || canStartBulkEmail || canStartScraperActions;",
    );
    expect(source).toContain('if (type === "bulk_email") return canStartBulkEmail;');
    expect(source).toContain("canOpenNewOperation ? (");
    expect(source).toContain("open={canOpenNewOperation && typeModalOpen}");
    expect(source).toContain("isTypeAllowed={canSelectNewOperationType}");
    expect(source).toContain("if (!canSelectNewOperationType(type)) return;");
    expect(modalSource).toContain("isTypeAllowed?: (type: OperationType) => boolean;");
    expect(modalSource).toContain("!isTypeAllowed || isTypeAllowed(item.type)");
  });

  it("allows scraper execute to open and select Enrichment and Scraper specialized entries", () => {
    expect(source).toContain(
      'if (type === "enrichment" || type === "scraper") return canStartScraperActions;',
    );
    expect(source).toContain("return canCreate;");
  });

  it("keeps operations execute for generic operation mutations", () => {
    expect(operationPermissionSource).toContain(
      'OPERATION_EXECUTE = "fair_crm.operations.execute"',
    );
    expect(source).toContain("const canExecute = can(OPERATION_EXECUTE)");
  });

  it("uses type-specific execute permissions for Bulk Email, Enrichment, and Scraper Start", () => {
    expect(source).toContain(
      'import { FAIR_EMAIL_PERMISSION_EXECUTE } from "../permissions/fairEmailPermissions";',
    );
    expect(source).toContain(
      'import { SCRAPER_PERMISSION_EXECUTE } from "../permissions/scraperPermissions";',
    );
    expect(source).toContain(
      "const canStartBulkEmail = can(FAIR_EMAIL_PERMISSION_EXECUTE);",
    );
    expect(source).toContain(
      "const canStartScraperActions = can(SCRAPER_PERMISSION_EXECUTE);",
    );
    expect(source).toContain(
      'if (operation.operation_type === "bulk_email") return canStartBulkEmail;',
    );
    expect(source).toContain('operation.operation_type === "enrichment" ||');
    expect(source).toContain('operation.operation_type === "scraper"');
    expect(source).toContain("return canStartScraperActions;");
    expect(source).toContain("return canExecute;");
    expect(source).toContain("if (!canStartOperation(operation)) return;");
    expect(source).toContain("canStartOperation(item) &&");
    expect(source).toContain("await startOperation(operation.id);");
  });

  it("keeps cancel on operations execute", () => {
    expect(source.match(/if \(!canExecute\) return;/g)).toHaveLength(1);
    expect(source).toContain("await cancelOperation(operation.id);");
    expect(source).toContain(
      'canExecute && ["draft", "ready", "active"].includes(item.status) ? (',
    );
  });
});
