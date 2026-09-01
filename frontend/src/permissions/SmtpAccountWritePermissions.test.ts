import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("../pages/SmtpAccountsPage.tsx", import.meta.url)),
  "utf8",
);

describe("SMTP account write permissions", () => {
  it("fails closed before create mutation", () => {
    expect(source).toContain("const handleCreate = async");
    expect(source).toContain("if (!canCreate) return;");
    expect(source).toContain('modal === "create" && canCreate');
  });

  it("fails closed before every update path", () => {
    expect(source).toContain("const performUpdate = async");
    expect(source).toContain("const handleUpdate = async");
    expect(source.match(/if \(!canUpdate\) return;/g)?.length).toBeGreaterThanOrEqual(2);
    expect(source).toContain("deactivateConfirmPayload && canUpdate");
  });

  it("fails closed before delete mutation", () => {
    expect(source).toContain("const handleDelete = async");
    expect(source).toContain("if (!canDelete) return;");
    expect(source).toContain("deleteTarget && canDelete");
  });

  it("preserves test-only edit access independently of update permission", () => {
    expect(source).toContain("testOnly={!canUpdate}");
    expect(source).toContain("onTestMail={canSendTestMail ? handleTestMail : undefined}");
  });
});
