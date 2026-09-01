import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  new URL("../pages/MailOperationsPage.tsx", import.meta.url),
  "utf8",
);

describe("MailOperationsPage retry permissions", () => {
  it("fails closed before retrying a mail operation", () => {
    expect(source).toContain('if (!canRetry || dialog?.type !== "retry") return;');
    expect(source).toContain("const canRetry = canSendMail(grantedPermissions);");
  });

  it("does not expose retry dialog or handler without execute permission", () => {
    expect(source).toContain('onRetry: canRetry ?');
    expect(source).toContain('dialog?.type === "retry" && canRetry');
  });
});
