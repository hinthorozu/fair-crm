export const FAIR_CRM_PERMISSION_CODES = [
  "fair_crm.email_accounts.read",
  "fair_crm.email_accounts.create",
  "fair_crm.email_accounts.update",
  "fair_crm.email_accounts.delete",
  "fair_crm.mail_templates.read",
  "fair_crm.mail_templates.create",
  "fair_crm.mail_templates.update",
  "fair_crm.mail_templates.delete",
  "fair_crm.mail_templates.render",
  "fair_crm.mail_templates.test_send",
  "fair_crm.fair_emails.preview",
  "fair_crm.fair_emails.send",
  "fair_crm.quotes.read",
  "fair_crm.quotes.create",
  "fair_crm.quotes.update",
  "fair_crm.quote_templates.read",
  "fair_crm.quote_templates.create",
  "fair_crm.quote_templates.update",
  "fair_crm.scraper.run",
  "fair_crm.template_contents.read",
  "fair_crm.template_contents.create",
  "fair_crm.template_contents.update",
  "fair_crm.template_contents.delete",
  "fair_crm.todos.read",
  "fair_crm.todos.create",
  "fair_crm.todos.update",
  "fair_crm.todos.archive",
  "fair_crm.todos.delete",
] as const;

const grantedPermissions = new Set<string>();

export function replaceGrantedPermissions(permissionCodes: readonly string[]): void {
  grantedPermissions.clear();
  for (const permissionCode of permissionCodes) {
    grantedPermissions.add(permissionCode);
  }
}

export function getGrantedCorePermissions(): Set<string> {
  return grantedPermissions;
}

async function checkCorePermission(
  coreBaseUrl: string,
  accessToken: string,
  organizationId: string,
  permissionCode: string,
): Promise<boolean> {
  const response = await fetch(
    `${coreBaseUrl}/api/v1/organizations/${encodeURIComponent(organizationId)}/authorization/check`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "X-Organization-Id": organizationId,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ permission_code: permissionCode }),
    },
  );

  if (response.status === 403) return false;
  if (!response.ok) {
    throw new Error(`Core authorization check failed (${response.status})`);
  }

  const data = (await response.json()) as { allowed?: boolean };
  return data.allowed === true;
}

export async function fetchGrantedCorePermissions(
  coreBaseUrl: string,
  accessToken: string,
  organizationId: string,
): Promise<string[]> {
  const decisions = await Promise.all(
    FAIR_CRM_PERMISSION_CODES.map(async (permissionCode) => ({
      permissionCode,
      allowed: await checkCorePermission(
        coreBaseUrl,
        accessToken,
        organizationId,
        permissionCode,
      ),
    })),
  );

  return decisions
    .filter((decision) => decision.allowed)
    .map((decision) => decision.permissionCode);
}
