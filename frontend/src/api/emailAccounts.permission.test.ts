import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { afterEach, describe, expect, it } from "vitest";
import { listEmailAccounts } from "./emailAccounts";
import {
  EMAIL_ACCOUNTS_PERMISSION_READ,
} from "../permissions/emailAccountPermissions";
import { replaceGrantedPermissions } from "../permissions/corePermissions";

const source = readFileSync(
  fileURLToPath(new URL("./emailAccounts.ts", import.meta.url)),
  "utf8",
);

afterEach(() => {
  replaceGrantedPermissions([]);
});

describe("email account list permission boundary", () => {
  it("fails closed before the HTTP lookup without email_accounts.read", async () => {
    replaceGrantedPermissions([]);

    await expect(listEmailAccounts()).rejects.toMatchObject({
      status: 403,
      message: expect.stringContaining(EMAIL_ACCOUNTS_PERMISSION_READ),
    });
  });

  it("keeps the canonical list endpoint behind the read-permission guard", () => {
    expect(source).toContain(
      "if (!hasPermission(getGrantedPermissions(), EMAIL_ACCOUNTS_PERMISSION_READ))",
    );
    expect(source).toContain("return apiRequest<EmailAccountListResponse>(EMAIL_ACCOUNTS_BASE);");
  });
});
