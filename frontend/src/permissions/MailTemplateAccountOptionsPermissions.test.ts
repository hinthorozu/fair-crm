import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const pageSource = readFileSync(
  fileURLToPath(new URL("../pages/MailTemplatesPage.tsx", import.meta.url)),
  "utf8",
);

const panelSource = readFileSync(
  fileURLToPath(
    new URL("../components/mail_templates/MailTemplateTestEmailPanel.tsx", import.meta.url),
  ),
  "utf8",
);

describe("mail template test-mail account permission consistency", () => {
  it("does not load email accounts without email_accounts.read", () => {
    expect(pageSource).toContain(
      "const canReadEmailAccounts = grantedPermissions.has(EMAIL_ACCOUNTS_PERMISSION_READ);",
    );
    expect(pageSource).toContain(
      "if (!canReadEmailAccounts) {\n      setEmailAccounts([]);\n      return;\n    }",
    );
    expect(pageSource).toContain("const response = await listEmailAccounts();");
    expect(pageSource).toContain("canChooseEmailAccount={canReadEmailAccounts}");
  });

  it("uses the organization default sender when account selection is unavailable", () => {
    expect(panelSource).toContain(
      "(!canChooseEmailAccount || Boolean(emailAccountId))",
    );
    expect(panelSource).toContain(
      "email_account_id: canChooseEmailAccount ? emailAccountId || null : null",
    );
    expect(panelSource).toContain("{canChooseEmailAccount ? (");
    expect(panelSource).toContain(
      "E-posta hesabı görüntüleme yetkisi olmadığı için kuruluşun varsayılan aktif hesabı kullanılacak.",
    );
  });

  it("preserves explicit account selection for authorized users", () => {
    expect(panelSource).toContain("<EmailAccountPicker");
    expect(panelSource).toContain("accounts={activeAccounts}");
    expect(panelSource).toContain("value={emailAccountId}");
    expect(panelSource).toContain("onChange={setEmailAccountId}");
  });
});
