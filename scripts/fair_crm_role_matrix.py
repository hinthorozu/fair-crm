"""Central FAIR CRM role → permission matrix (Core RBAC role templates)."""

from __future__ import annotations

from typing import Final

AUDIT_READ_PERMISSION: Final = "audit.logs.read"
ROLE_MATRIX_VERSION: Final = 13

ALL_FAIR_CRM_PERMISSIONS: tuple[str, ...] = (
    "fair_crm.customers.create",
    "fair_crm.customers.read",
    "fair_crm.customers.update",
    "fair_crm.customers.archive",
    "fair_crm.fairs.read",
    "fair_crm.fairs.create",
    "fair_crm.fairs.update",
    "fair_crm.fairs.archive",
    "fair_crm.imports.read",
    "fair_crm.imports.create",
    "fair_crm.imports.update",
    "fair_crm.imports.delete",
    "fair_crm.imports.apply",
    "fair_crm.contacts.read",
    "fair_crm.contacts.create",
    "fair_crm.contacts.update",
    "fair_crm.contacts.delete",
    "fair_crm.participations.read",
    "fair_crm.participations.create",
    "fair_crm.participations.update",
    "fair_crm.participations.delete",
    "fair_crm.activities.read",
    "fair_crm.activities.create",
    "fair_crm.activities.update",
    "fair_crm.activities.delete",
    "fair_crm.scraper.read",
    "fair_crm.scraper.create",
    "fair_crm.scraper.update",
    "fair_crm.scraper.delete",
    "fair_crm.scraper.execute",
    "fair_crm.operations.read",
    "fair_crm.operations.create",
    "fair_crm.operations.execute",
    "fair_crm.email_accounts.read",
    "fair_crm.email_accounts.create",
    "fair_crm.email_accounts.update",
    "fair_crm.email_accounts.delete",
    "fair_crm.mail_templates.read",
    "fair_crm.mail_templates.create",
    "fair_crm.mail_templates.update",
    "fair_crm.mail_templates.delete",
    "fair_crm.mail_templates.execute",
    "fair_crm.quote_templates.read",
    "fair_crm.quote_templates.create",
    "fair_crm.quote_templates.update",
    "fair_crm.template_contents.read",
    "fair_crm.template_contents.create",
    "fair_crm.template_contents.update",
    "fair_crm.template_contents.delete",
    "fair_crm.quotes.read",
    "fair_crm.quotes.create",
    "fair_crm.quotes.update",
    "fair_crm.quotes.delete",
    "fair_crm.fair_emails.preview",
    "fair_crm.fair_emails.execute",
    "fair_crm.admin.backups.read",
    "fair_crm.admin.backups.create",
    "fair_crm.admin.backups.execute",
    "fair_crm.admin.data_operations.read",
    "fair_crm.admin.data_operations.execute",
    "fair_crm.todos.read",
    "fair_crm.todos.create",
    "fair_crm.todos.update",
    "fair_crm.todos.archive",
    "fair_crm.todos.delete",
    "fair_crm.todos.outcomes.read",
    "fair_crm.todos.outcomes.create",
    "fair_crm.todos.outcomes.update",
    "fair_crm.todos.outcomes.deactivate",
    "fair_crm.dashboard.read",
)

IDENTITY_ADMIN_PERMISSIONS: tuple[str, ...] = (
    "identity.users.read",
    "identity.users.create",
    "identity.users.update",
    "identity.roles.read",
    "identity.roles.update",
)

ADMIN_ONLY_PERMISSIONS: frozenset[str] = frozenset(
    {
        "fair_crm.admin.backups.read",
        "fair_crm.admin.backups.create",
        "fair_crm.admin.backups.execute",
        "fair_crm.admin.data_operations.read",
        "fair_crm.admin.data_operations.execute",
        "fair_crm.email_accounts.create",
        "fair_crm.email_accounts.update",
        "fair_crm.email_accounts.delete",
        "fair_crm.mail_templates.create",
        "fair_crm.mail_templates.update",
        "fair_crm.mail_templates.delete",
        "fair_crm.mail_templates.execute",
        "fair_crm.quote_templates.create",
        "fair_crm.quote_templates.update",
        "fair_crm.template_contents.create",
        "fair_crm.template_contents.update",
        "fair_crm.template_contents.delete",
        "fair_crm.quotes.delete",
        "fair_crm.fair_emails.execute",
        "fair_crm.scraper.create",
        "fair_crm.scraper.update",
        "fair_crm.scraper.delete",
        "fair_crm.todos.delete",
        "fair_crm.todos.outcomes.create",
        "fair_crm.todos.outcomes.update",
        "fair_crm.todos.outcomes.deactivate",
    }
)

_FULL_ACCESS_PERMISSIONS: tuple[str, ...] = (
    ALL_FAIR_CRM_PERMISSIONS + IDENTITY_ADMIN_PERMISSIONS + (AUDIT_READ_PERMISSION,)
)

# Platform-level unrestricted access is NOT a role. It is represented only by
# identity_users.is_super_admin. OrganizationAdmin is the organization RBAC role.
ROLE_DEFINITIONS: dict[str, dict[str, object]] = {
    "organization_admin": {
        "name": "OrganizationAdmin",
        "permissions": _FULL_ACCESS_PERMISSIONS,
    },
}

# The bootstrap user is also attached to the default organization as its
# OrganizationAdmin. Its platform-level Super Admin state is controlled solely
# by identity_users.is_super_admin in Core, not by this role mapping.
DEV_ROLE_USERS: tuple[tuple[str, str, str], ...] = (
    ("organization_admin", "dev@example.com", "00000000-0000-4000-8000-000000000001"),
)


def role_slugs() -> tuple[str, ...]:
    return tuple(ROLE_DEFINITIONS.keys())


def permissions_for_role(slug: str) -> frozenset[str]:
    definition = ROLE_DEFINITIONS.get(slug)
    if definition is None:
        raise KeyError(f"Unknown role slug: {slug}")
    return frozenset(definition["permissions"])  # type: ignore[arg-type]


def all_permissions_referenced() -> frozenset[str]:
    codes: set[str] = set()
    for slug in role_slugs():
        codes.update(permissions_for_role(slug))
    return frozenset(codes)
