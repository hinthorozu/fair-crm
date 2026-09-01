import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  new URL("../pages/MailOperationsPage.tsx", import.meta.url),
  "utf8",
);

describe("MailOperationsPage email account lookup permissions", () => {
  it("skips the optional email-account lookup without read permission", () => {
    expect(source).toContain(
      'const canReadEmailAccounts = canPerformEmailAccountAction(grantedPermissions, "read");',
    );
    expect(source).toContain("if (!canReadEmailAccounts) {");
    expect(source).toContain("}, [canReadEmailAccounts]);");
  });

  it("does not expose the SMTP account filter without read permission", () => {
    expect(source).toContain("{canReadEmailAccounts ? (");
    expect(source).toContain('htmlFor="mail-operations-smtp"');
  });
});
