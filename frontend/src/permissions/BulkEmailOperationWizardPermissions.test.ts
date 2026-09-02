import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  new URL("../pages/BulkEmailOperationWizardPage.tsx", import.meta.url),
  "utf8",
);

describe("BulkEmailOperationWizardPage permissions", () => {
  it("uses one canonical permission for each bulk email action", () => {
    expect(source).toContain(
      'const FAIR_EMAIL_PREVIEW_PERMISSION = "fair_crm.fair_emails.preview";',
    );
    expect(source).toContain(
      'const FAIR_EMAIL_EXECUTE_PERMISSION = "fair_crm.fair_emails.execute";',
    );
    expect(source).toContain("const canPreviewBulkEmail = can(FAIR_EMAIL_PREVIEW_PERMISSION);");
    expect(source).toContain("const canSendBulkEmail = can(FAIR_EMAIL_EXECUTE_PERMISSION);");
    expect(source).not.toContain("PERMISSION_OPERATIONS_CREATE");
    expect(source).not.toContain("OPERATION_EXECUTE");
  });

  it("fails closed before preview and send operations", () => {
    expect(source).toContain("if (!canPreviewBulkEmail) {");
    expect(source).toContain("const result = await previewBulkEmailOperation({");
    expect(source).toContain("const handleSend = async () => {");
    expect(source).toContain("if (!canSendBulkEmail) return;");
    expect(source).toContain("const result = await sendBulkEmailOperation({");
  });

  it("keeps preview optional for execute-only send", () => {
    expect(source).toContain("const canProceedMailSettings =\r\n    !templatesLoading &&");
    expect(source).toContain("const previewRequirementSatisfied =");
    expect(source).toContain("!canPreviewBulkEmail ||");
    expect(source).toContain("const canProceedSummary = previewRequirementSatisfied;");
    expect(source).toContain('currentStep.id === "summary" && canPreviewBulkEmail');
    expect(source).toContain("setPreviewing(canPreviewBulkEmail);");
    expect(source).toContain("canPreviewBulkEmail &&\r\n      (!previewReady ||");
    expect(source).toContain("const canSend = canSendBulkEmail && canProceedSummary && !sending;");
    expect(source).toContain('currentStep.id === "summary" && canSendBulkEmail ? (');
    expect(source).toContain(") : canPreviewBulkEmail ? (");
  });
});
