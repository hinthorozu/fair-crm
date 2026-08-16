export const FAIR_CRM_PERMISSION_CODES = [
  "identity.users.read",
  "identity.users.create",
  "identity.users.update",
  "identity.users.delete",
  "identity.roles.read",
  "identity.roles.create",
  "identity.roles.update",
  "identity.roles.delete",
  "identity.roles.assign",
  "identity.roles.assign_protected",
  "identity.role_templates.read",
  "identity.role_templates.manage",
  "identity.permissions.read",
  "identity.permissions.lifecycle",
  "fair_crm.activities.create",
  "fair_crm.activities.delete",
  "fair_crm.activities.read",
  "fair_crm.activities.update",
  "fair_crm.admin.backups.create",
  "fair_crm.admin.backups.download",
  "fair_crm.admin.backups.read",
  "fair_crm.admin.data_operations.read",
  "fair_crm.admin.data_operations.run",
  "fair_crm.contacts.create",
  "fair_crm.contacts.delete",
  "fair_crm.contacts.read",
  "fair_crm.contacts.update",
  "fair_crm.cost_catalog.categories.read",
  "fair_crm.cost_catalog.categories.create",
  "fair_crm.cost_catalog.categories.update",
  "fair_crm.cost_catalog.categories.delete",
  "fair_crm.cost_catalog.products.read",
  "fair_crm.cost_catalog.products.create",
  "fair_crm.cost_catalog.products.update",
  "fair_crm.cost_catalog.products.delete",
  "fair_crm.customers.create",
  "fair_crm.customers.delete",
  "fair_crm.customers.read",
  "fair_crm.customers.update",
  "fair_crm.email_accounts.read",
  "fair_crm.email_accounts.create",
  "fair_crm.email_accounts.update",
  "fair_crm.email_accounts.delete",
  "fair_crm.fairs.create",
  "fair_crm.fairs.delete",
  "fair_crm.fairs.read",
  "fair_crm.fairs.update",
  "fair_crm.imports.apply",
  "fair_crm.imports.create",
  "fair_crm.imports.delete",
  "fair_crm.imports.read",
  "fair_crm.imports.update",
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
  "fair_crm.quotes.delete",
  "fair_crm.quote_templates.read",
  "fair_crm.quote_templates.create",
  "fair_crm.quote_templates.update",
  "fair_crm.operations.create",
  "fair_crm.operations.execute",
  "fair_crm.operations.read",
  "fair_crm.operations.update",
  "fair_crm.participations.create",
  "fair_crm.participations.delete",
  "fair_crm.participations.read",
  "fair_crm.participations.update",
  "fair_crm.scraper.create",
  "fair_crm.scraper.delete",
  "fair_crm.scraper.download",
  "fair_crm.scraper.read",
  "fair_crm.scraper.run",
  "fair_crm.scraper.update",
  "fair_crm.template_contents.read",
  "fair_crm.template_contents.create",
  "fair_crm.template_contents.update",
  "fair_crm.template_contents.delete",
  "fair_crm.todos.read",
  "fair_crm.todos.create",
  "fair_crm.todos.update",
  "fair_crm.todos.delete",
  "fair_crm.todos.outcomes.create",
  "fair_crm.todos.outcomes.delete",
  "fair_crm.todos.outcomes.read",
  "fair_crm.todos.outcomes.update",
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
