"""Central FAIR CRM dev role → permission matrix (Core RBAC role templates)."""

from __future__ import annotations

from typing import Final

AUDIT_READ_PERMISSION: Final = "audit.logs.read"
ROLE_MATRIX_VERSION: Final = 1

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
    "fair_crm.scraper.run",
    "fair_crm.scraper.download",
    "fair_crm.smtp.read",
    "fair_crm.smtp.create",
    "fair_crm.smtp.update",
    "fair_crm.smtp.delete",
    "fair_crm.mail_templates.read",
    "fair_crm.mail_templates.create",
    "fair_crm.mail_templates.update",
    "fair_crm.mail_templates.delete",
    "fair_crm.mail_templates.render",
    "fair_crm.mail_templates.test_send",
    "fair_crm.fair_emails.preview",
    "fair_crm.fair_emails.send",
    "fair_crm.admin.backups.read",
    "fair_crm.admin.backups.create",
    "fair_crm.admin.backups.download",
    "fair_crm.admin.data_operations.read",
    "fair_crm.admin.data_operations.run",
    "fair_crm.todos.read",
    "fair_crm.todos.create",
    "fair_crm.todos.update",
    "fair_crm.todos.archive",
    "fair_crm.todos.delete",
    "fair_crm.todos.outcomes.read",
    "fair_crm.todos.outcomes.create",
    "fair_crm.todos.outcomes.update",
    "fair_crm.todos.outcomes.deactivate",
)

ADMIN_ONLY_PERMISSIONS: frozenset[str] = frozenset(
    {
        "fair_crm.admin.backups.read",
        "fair_crm.admin.backups.create",
        "fair_crm.admin.backups.download",
        "fair_crm.admin.data_operations.read",
        "fair_crm.admin.data_operations.run",
        "fair_crm.smtp.create",
        "fair_crm.smtp.update",
        "fair_crm.smtp.delete",
        "fair_crm.mail_templates.create",
        "fair_crm.mail_templates.update",
        "fair_crm.mail_templates.delete",
        "fair_crm.mail_templates.render",
        "fair_crm.mail_templates.test_send",
        "fair_crm.fair_emails.send",
        "fair_crm.scraper.create",
        "fair_crm.scraper.update",
        "fair_crm.scraper.delete",
        "fair_crm.todos.delete",
        "fair_crm.todos.outcomes.create",
        "fair_crm.todos.outcomes.update",
        "fair_crm.todos.outcomes.deactivate",
    }
)

_MANAGER_PERMISSIONS: tuple[str, ...] = (
    "fair_crm.customers.read",
    "fair_crm.customers.create",
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
    "fair_crm.smtp.read",
    "fair_crm.mail_templates.read",
    "fair_crm.fair_emails.preview",
    "fair_crm.scraper.read",
    "fair_crm.scraper.run",
    "fair_crm.scraper.download",
    "fair_crm.todos.read",
    "fair_crm.todos.create",
    "fair_crm.todos.update",
    "fair_crm.todos.archive",
    "fair_crm.todos.outcomes.read",
)

_SALES_PERMISSIONS: tuple[str, ...] = (
    "fair_crm.customers.read",
    "fair_crm.customers.create",
    "fair_crm.customers.update",
    "fair_crm.fairs.read",
    "fair_crm.imports.read",
    "fair_crm.contacts.read",
    "fair_crm.contacts.create",
    "fair_crm.contacts.update",
    "fair_crm.participations.read",
    "fair_crm.participations.create",
    "fair_crm.participations.update",
    "fair_crm.activities.read",
    "fair_crm.activities.create",
    "fair_crm.activities.update",
    "fair_crm.smtp.read",
    "fair_crm.mail_templates.read",
    "fair_crm.fair_emails.preview",
    "fair_crm.todos.read",
    "fair_crm.todos.create",
    "fair_crm.todos.update",
    "fair_crm.todos.archive",
    "fair_crm.todos.outcomes.read",
)

_VIEWER_PERMISSIONS: tuple[str, ...] = (
    "fair_crm.customers.read",
    "fair_crm.fairs.read",
    "fair_crm.imports.read",
    "fair_crm.contacts.read",
    "fair_crm.participations.read",
    "fair_crm.activities.read",
    "fair_crm.scraper.read",
    "fair_crm.smtp.read",
    "fair_crm.mail_templates.read",
    "fair_crm.fair_emails.preview",
    "fair_crm.todos.read",
    "fair_crm.todos.outcomes.read",
)

_SCRAPER_OPERATOR_PERMISSIONS: tuple[str, ...] = (
    "fair_crm.fairs.read",
    "fair_crm.scraper.read",
    "fair_crm.scraper.run",
    "fair_crm.scraper.download",
)

_FULL_ACCESS_PERMISSIONS: tuple[str, ...] = ALL_FAIR_CRM_PERMISSIONS + (AUDIT_READ_PERMISSION,)

ROLE_DEFINITIONS: dict[str, dict[str, object]] = {
    "owner": {
        "name": "Owner",
        "permissions": _FULL_ACCESS_PERMISSIONS,
    },
    "admin": {
        "name": "Admin",
        "permissions": _FULL_ACCESS_PERMISSIONS,
    },
    "manager": {
        "name": "Manager",
        "permissions": _MANAGER_PERMISSIONS,
    },
    "sales": {
        "name": "Sales",
        "permissions": _SALES_PERMISSIONS,
    },
    "viewer": {
        "name": "Viewer",
        "permissions": _VIEWER_PERMISSIONS,
    },
    "scraper_operator": {
        "name": "Scraper Operator",
        "permissions": _SCRAPER_OPERATOR_PERMISSIONS,
    },
    "member": {
        "name": "Member",
        "permissions": (),
    },
}

DEV_ROLE_USERS: tuple[tuple[str, str, str], ...] = (
    ("owner", "dev@example.com", "00000000-0000-4000-8000-000000000001"),
    ("admin", "dev-admin@example.com", "00000000-0000-4000-8000-000000000002"),
    ("manager", "dev-manager@example.com", "00000000-0000-4000-8000-000000000003"),
    ("sales", "dev-sales@example.com", "00000000-0000-4000-8000-000000000004"),
    ("viewer", "dev-viewer@example.com", "00000000-0000-4000-8000-000000000005"),
    ("scraper_operator", "dev-scraper@example.com", "00000000-0000-4000-8000-000000000006"),
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
