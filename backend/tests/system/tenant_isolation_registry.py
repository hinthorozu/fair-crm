"""Canonical FAIR CRM tenant-isolation evidence registry.

Every top-level product module that carries ``organization_id`` in production code
must be represented here or explicitly excluded with an architectural reason.
The system governance test discovers scoped modules from production code and
fails CI when a new scoped module is not registered.

Evidence paths are relative to ``backend/tests`` and may point to a test file or
an entire test directory. They must contain executable ABC/XYZ-style negative
evidence (foreign/cross-organization denial), not only happy-path tests.
"""

from __future__ import annotations


TENANT_ISOLATION_EVIDENCE: dict[str, tuple[str, ...]] = {
    "activities": ("modules/test_p0_1_final_contact_activity_tenant_isolation.py",),
    "contacts": ("modules/test_p0_1_final_contact_activity_tenant_isolation.py",),
    "cost_catalog": ("modules/test_p0_1_final_tenant_isolation_certification.py",),
    "customers": ("modules/customers",),
    "dashboard": ("modules/dashboard",),
    "data_integration": ("modules/data_integration",),
    "data_operations": ("modules/data_operations",),
    "email_accounts": ("modules/email_accounts",),
    "email_delivery": ("modules/email_delivery",),
    "email_webhooks": ("modules/email_webhooks",),
    "fair_emails": ("modules/fair_emails",),
    "fairs": ("modules/fairs",),
    "imports": (
        "modules/imports",
        "modules/test_p0_1_final_tenant_isolation_certification.py",
    ),
    "mail_send_operations": ("modules/mail_send_operations",),
    "mail_templates": ("modules/mail_templates",),
    "operations": ("modules/operations",),
    "quotes": ("modules/quotes",),
    "scraper": ("modules/scraper",),
    "template_management": ("modules/template_management",),
    "todos": ("modules/todos",),
}


# Exclusions are intentionally rare. A module may be excluded only when it
# references organization context but does not own/read/mutate organization-
# scoped product data. Every exclusion needs a durable architectural reason.
TENANT_SCOPE_EXCLUSIONS: dict[str, str] = {
    "auth": (
        "Auth adapts trusted Core identity/organization context; it does not own "
        "organization-scoped FAIR CRM domain resources."
    ),
}
