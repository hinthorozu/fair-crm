import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  new URL("../components/fairs/FairBulkEmailWizard.tsx", import.meta.url),
  "utf8",
).replace(/\r\n/g, "\n");

describe("FairBulkEmailWizard supporting email-account permissions", () => {
  it("keeps preview hydration independent from email_accounts.read", () => {
    expect(source).toContain(
      'getGrantedPermissions as getGrantedEmailAccountPermissions',
    );
    expect(source).toContain(
      'const canReadEmailAccounts = canPerformEmailAccountAction(emailAccountPermissions, "read");',
    );
    expect(source).toContain("listMailTemplates(),");
    expect(source).toContain("canReadEmailAccounts\n            ? listEmailAccounts()");
    expect(source).toContain(": Promise.resolve([] as EmailAccount[])");
    expect(source).toContain(".catch(() => [] as EmailAccount[])");
  });

  it("keeps SMTP-backed send fail closed without account read access", () => {
    expect(source).toContain("const canSubmit =\n    canSend &&\n    canReadEmailAccounts &&");
    expect(source).toContain("{canReadEmailAccounts ? (\n            <EmailAccountPicker");
    expect(source).toContain("{canSend && canReadEmailAccounts ? (\n          <button");
  });

  it("does not add email account permission to preview readiness", () => {
    const previewBlock = source.slice(
      source.indexOf("const canRunPreview ="),
      source.indexOf("const canSubmit ="),
    );
    expect(previewBlock).toContain("canPreview &&");
    expect(previewBlock).toContain("canRenderMailTemplate &&");
    expect(previewBlock).not.toContain("canReadEmailAccounts");
  });
});
