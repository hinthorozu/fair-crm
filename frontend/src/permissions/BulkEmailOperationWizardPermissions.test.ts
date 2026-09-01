import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  new URL("../pages/BulkEmailOperationWizardPage.tsx", import.meta.url),
  "utf8",
);

describe("BulkEmailOperationWizardPage permissions", () => {
  it("uses the canonical preview and send capability sets", () => {
    expect(source).toContain(
      'const FAIR_EMAIL_PREVIEW_PERMISSION = "fair_crm.fair_emails.preview";',
    );
    expect(source).toContain(
      'const FAIR_EMAIL_EXECUTE_PERMISSION = "fair_crm.fair_emails.execute";',
    );
    expect(source).toContain("const canPreviewBulkEmail = can(FAIR_EMAIL_PREVIEW_PERMISSION);");
    expect(source).toContain("can(PERMISSION_OPERATIONS_CREATE) &&");
    expect(source).toContain("can(OPERATION_EXECUTE) &&");
    expect(source).toContain("can(FAIR_EMAIL_EXECUTE_PERMISSION);");
  });

  it("fails closed before preview and send operations", () => {
    expect(source).toContain("if (!canPreviewBulkEmail) {");
    expect(source).toContain("const result = await previewBulkEmailOperation({");
    expect(source).toContain("const handleSend = async () => {");
    expect(source).toContain("if (!canSendBulkEmail) return;");
    expect(source).toContain("const result = await sendBulkEmailOperation({");
  });

  it("gates summary navigation and the send affordance", () => {
    expect(source).toContain("const canProceedMailSettings =\r\n    canPreviewBulkEmail &&");
    expect(source).toContain("const canSend = canSendBulkEmail && canProceedSummary && !sending;");
    expect(source).toContain('currentStep.id === "summary" && canSendBulkEmail ? (');
  });
});
