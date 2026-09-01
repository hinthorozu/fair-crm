import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const detailSource = readFileSync(
  new URL("../components/DuplicateGroupDetailView.tsx", import.meta.url),
  "utf8",
);
const summarySource = readFileSync(
  new URL("../components/duplicateMerge/MergeSummaryPanel.tsx", import.meta.url),
  "utf8",
);

describe("duplicate group merge execute permission", () => {
  it("uses the canonical data operations execute capability", () => {
    expect(detailSource).toContain(
      'const DATA_OPERATIONS_EXECUTE_PERMISSION = "fair_crm.admin.data_operations.execute";',
    );
    expect(detailSource).toContain("const canExecuteDataOperations = can(DATA_OPERATIONS_EXECUTE_PERMISSION);");
  });

  it("fails closed before opening or executing a merge", () => {
    expect(detailSource.match(/if \(!canExecuteDataOperations\) return;/g)?.length).toBeGreaterThanOrEqual(2);
    expect(detailSource).toContain("open={mergeConfirmOpen && canExecuteDataOperations}");
  });

  it("keeps preview readable but hides the execute affordance", () => {
    expect(detailSource).toContain("previewDuplicateGroupMerge(");
    expect(detailSource).toContain("canExecute={canExecuteDataOperations}");
    expect(summarySource).toContain("{canExecute ? (");
    expect(summarySource).toContain("onClick={onMergeExecute}");
  });
});
