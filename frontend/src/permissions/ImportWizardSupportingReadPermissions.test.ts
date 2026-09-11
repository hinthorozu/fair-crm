import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("../pages/ImportWizardPage.tsx", import.meta.url)),
  "utf8",
);

describe("Import wizard supporting read permissions", () => {
  it("uses canonical fair and participation read permissions", () => {
    expect(source).toContain('import { FAIR_READ } from "../permissions/fairPermissions"');
    expect(source).toContain(
      'import { PARTICIPATION_READ } from "../permissions/participationPermissions"',
    );
    expect(source).toContain("const canFairRead = can(FAIR_READ)");
    expect(source).toContain("const canParticipationRead = can(PARTICIPATION_READ)");
  });

  it("does not issue supporting reads without their effective permission", () => {
    expect(source).toContain(
      "if (!canFairRead) {\n      setSelectedFair(null);\n      return;\n    }",
    );
    expect(source).toContain("if (!canParticipationRead) return;");
  });

  it("keeps fair hydration independent from participant-count failures", () => {
    expect(source).toContain(
      "const fair = await getFair(fairId);\n      setSelectedFair(fair);",
    );
    expect(source).toContain(
      "const parts = await listParticipantsByFair(fairId, { page: 1, pageSize: 1 });\n      setParticipantCount(parts.pagination.totalItems);\n    } catch {\n      setParticipantCount(null);",
    );
  });

  it("keeps a preselected fair fixed instead of falling back to the fair selector", () => {
    expect(source).toContain("{preselectedFairId ? (\n        selectedFair ? (");
    expect(source).toContain(
      ") : null\n      ) : (\n        <FairEntitySelect",
    );
  });
});
