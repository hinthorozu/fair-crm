from __future__ import annotations

from datetime import UTC, datetime
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.integrations.kyrox_core.ports import AuthContext
from app.main import create_app
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.email_accounts.infrastructure.persistence.models import (
    EmailAccountModel,
    EmailAccountSmtpConfigModel,
)
from app.modules.organization_closure.application.export_planner import (
    DATA_CLASS_REGISTRY,
    DEFERRED,
    EXCLUDED,
    FORBIDDEN_EXPORT_SOURCE_TABLES,
    INCLUDED,
    ClosureExportPlanNotFoundError,
    ClosureExportPlanningError,
    OrganizationClosureExportPlanner,
    included_source_table_names,
)
from app.modules.organization_closure.application.service import (
    ClosureLifecyclePreconditionError,
    ClosurePermissionDeniedError,
    OrganizationClosureService,
)
from app.modules.organization_closure.infrastructure.export_plan_repository import (
    SqlAlchemyOrganizationClosureExportPlanRepository,
)
from app.modules.organization_closure.infrastructure.models import (
    OrganizationClosureEventModel,
    OrganizationClosureExportPlanModel,
)
from app.modules.organization_closure.infrastructure.repository import (
    SqlAlchemyOrganizationClosureRepository,
)
from app.modules.quote_templates.infrastructure.models import (
    QuoteTemplateModel,
    QuoteTemplateVersionModel,
)


class FakeAuthorization:
    def __init__(self, *, allowed: bool = True) -> None:
        self.allowed = allowed
        self.calls: list[dict[str, object]] = []

    def check_permission(self, **kwargs: object) -> bool:
        self.calls.append(kwargs)
        return self.allowed


class FakeLifecycle:
    def __init__(self, *, status: str = "suspended") -> None:
        self.status = status
        self.calls: list[object] = []

    def get_snapshot(self, organization_id: object) -> SimpleNamespace:
        self.calls.append(organization_id)
        return SimpleNamespace(status=self.status)


class RecordingAudit:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def record_event(self, **kwargs: object) -> None:
        self.events.append(kwargs)


def _auth(organization_id):
    return AuthContext(
        user_id=uuid4(),
        email="platform-admin@example.com",
        session_id=uuid4(),
        organization_id=organization_id,
    )


def _start_closure(db_session, organization_id):
    auth = _auth(organization_id)
    service = OrganizationClosureService(
        SqlAlchemyOrganizationClosureRepository(db_session),
        FakeAuthorization(),
        FakeLifecycle(),
        RecordingAudit(),
    )
    execution = service.start(
        organization_id=organization_id,
        idempotency_key=f"ol08-03a-{uuid4()}",
        auth=auth,
        access_token="token",
    )
    db_session.flush()
    return execution, auth


def _planner(db_session, *, allowed: bool = True, lifecycle_status: str = "suspended"):
    repository = SqlAlchemyOrganizationClosureExportPlanRepository(db_session)
    authorization = FakeAuthorization(allowed=allowed)
    lifecycle = FakeLifecycle(status=lifecycle_status)
    audit = RecordingAudit()
    planner = OrganizationClosureExportPlanner(
        repository,
        authorization,
        lifecycle,
        audit,
    )
    return planner, repository, authorization, lifecycle, audit


def _customer(organization_id, *, customer_id=None):
    now = datetime.now(tz=UTC)
    return CustomerModel(
        id=customer_id or uuid4(),
        organization_id=organization_id,
        display_name="Export Planner Customer",
        legal_name=None,
        trade_name=None,
        normalized_name=f"export-planner-{uuid4()}",
        customer_type="company",
        status="active",
        tax_number=None,
        tax_office=None,
        country="TR",
        city="Istanbul",
        district=None,
        address=None,
        description=None,
        instagram_url=None,
        facebook_url=None,
        linkedin_url=None,
        youtube_url=None,
        source="manual",
        email_allowed=True,
        sms_allowed=True,
        email_unsubscribed_at=None,
        sms_unsubscribed_at=None,
        consent_note=None,
        created_at=now,
        updated_at=now,
        deleted_at=None,
        archived_from_status=None,
    )


def _data_class(manifest: dict, key: str) -> dict:
    return next(item for item in manifest["data_classes"] if item["key"] == key)


def _source(data_class: dict, key: str) -> dict:
    return next(item for item in data_class["sources"] if item["key"] == key)


def test_registry_explicitly_covers_accepted_v1_classes() -> None:
    keys = {item.key for item in DATA_CLASS_REGISTRY}
    required = {
        "customers",
        "customer_communications",
        "contacts",
        "fairs",
        "participations",
        "activities_followups",
        "todos_workflow",
        "quotes",
        "quote_template_sources",
        "template_content_sources",
        "cost_catalog",
        "imports_data_integration",
        "scraper_enrichment_structured",
        "operations_automation_structured",
        "mail_templates",
        "mail_send_history",
        "generated_binary_files_artifacts",
        "reusable_provider_smtp_credentials",
        "system_admin_backups_restores",
    }
    assert required <= keys
    assert all(item.classification in {INCLUDED, EXCLUDED, DEFERRED} for item in DATA_CLASS_REGISTRY)
    assert all(item.reason_code for item in DATA_CLASS_REGISTRY)


def test_secret_bearing_tables_are_structurally_forbidden_as_sources() -> None:
    assert included_source_table_names().isdisjoint(FORBIDDEN_EXPORT_SOURCE_TABLES)
    secret_class = next(
        item
        for item in DATA_CLASS_REGISTRY
        if item.key == "reusable_provider_smtp_credentials"
    )
    assert secret_class.classification == EXCLUDED
    assert secret_class.reason_code == "reusable_secret_material_forbidden"
    assert secret_class.sources == ()


def test_plan_counts_only_target_organization_and_is_idempotent(
    db_session,
    organization_id,
    other_organization_id,
) -> None:
    execution, auth = _start_closure(db_session, organization_id)
    own_customer = _customer(organization_id)
    foreign_customer = _customer(other_organization_id)
    db_session.add_all([own_customer, foreign_customer])
    db_session.flush()

    planner, _, authorization, lifecycle, audit = _planner(db_session)
    first = planner.plan(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )
    second = planner.plan(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )

    assert second.id == first.id
    assert second.manifest_digest == first.manifest_digest
    assert first.status == "planned"
    assert first.disposition == "required"
    assert first.manifest_json["planning_state"] == "planned"
    assert first.manifest_json["digest_semantics"] == "planning_metadata_only_not_package_integrity"

    customers = _data_class(first.manifest_json, "customers")
    customer_source = _source(customers, "customers")
    assert customer_source["record_count"] == 1
    assert customers["record_count"] == 1
    assert str(own_customer.id) not in json.dumps(first.manifest_json)
    assert str(foreign_customer.id) not in json.dumps(first.manifest_json)

    assert authorization.calls[0]["permission_code"] == "identity.organizations.delete"
    assert lifecycle.calls == [organization_id, organization_id]
    planned_audits = [
        event
        for event in audit.events
        if event.get("action") == "organization_closure.export_plan.planned"
    ]
    assert len(planned_audits) == 1

    local_events = list(
        db_session.scalars(
            select(OrganizationClosureEventModel).where(
                OrganizationClosureEventModel.execution_id == execution.id,
                OrganizationClosureEventModel.action == "export_plan_planned",
            )
        ).all()
    )
    assert len(local_events) == 1


def test_parent_join_scope_for_quote_template_versions_excludes_foreign_rows(
    db_session,
    organization_id,
    other_organization_id,
) -> None:
    execution, auth = _start_closure(db_session, organization_id)
    now = datetime.now(tz=UTC)
    own_template = QuoteTemplateModel(
        id=uuid4(),
        organization_id=organization_id,
        name="Own template",
        current_version_id=None,
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )
    foreign_template = QuoteTemplateModel(
        id=uuid4(),
        organization_id=other_organization_id,
        name="Foreign template",
        current_version_id=None,
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )
    db_session.add_all([own_template, foreign_template])
    db_session.flush()
    db_session.add_all(
        [
            QuoteTemplateVersionModel(
                id=uuid4(),
                template_id=own_template.id,
                version_number=1,
                logo_url=None,
                source_code="own",
                created_at=now,
                created_by=auth.user_id,
            ),
            QuoteTemplateVersionModel(
                id=uuid4(),
                template_id=foreign_template.id,
                version_number=1,
                logo_url=None,
                source_code="foreign",
                created_at=now,
                created_by=uuid4(),
            ),
        ]
    )
    db_session.flush()

    planner, _, _, _, _ = _planner(db_session)
    plan = planner.plan(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )

    templates = _data_class(plan.manifest_json, "quote_template_sources")
    versions = _source(templates, "quote_template_versions")
    assert versions["scope_mode"] == "parent_join"
    assert versions["record_count"] == 1
    assert templates["record_count"] == 2


def test_secret_values_never_enter_manifest_or_fingerprints(db_session, organization_id) -> None:
    execution, auth = _start_closure(db_session, organization_id)
    now = datetime.now(tz=UTC)
    account = EmailAccountModel(
        id=uuid4(),
        organization_id=organization_id,
        name="Secret-bearing SMTP account",
        account_type="smtp",
        provider_key=None,
        from_email="sender@example.com",
        from_name="Sender",
        is_default=True,
        is_active=True,
        max_delivery_attempts=3,
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )
    sentinel_secret = "OL08-SECRET-SENTINEL-DO-NOT-EXPORT"
    db_session.add(account)
    db_session.flush()
    db_session.add(
        EmailAccountSmtpConfigModel(
            email_account_id=account.id,
            host="smtp.example.com",
            port=587,
            username="sender@example.com",
            password=sentinel_secret,
            encryption_type="starttls",
        )
    )
    db_session.flush()

    planner, _, _, _, audit = _planner(db_session)
    plan = planner.plan(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )

    serialized_manifest = json.dumps(plan.manifest_json, sort_keys=True)
    serialized_audit = json.dumps(audit.events, sort_keys=True, default=str)
    assert sentinel_secret not in serialized_manifest
    assert sentinel_secret not in serialized_audit
    assert "email_account_smtp_configs" not in serialized_manifest
    assert plan.manifest_json["secret_exclusion"] == {
        "status": "enforced",
        "fingerprint_input": "record_id_only",
        "reusable_secret_material": "excluded",
        "secret_derived_fingerprints": "forbidden",
    }


def test_failed_read_only_planning_persists_no_false_success_and_can_retry(
    monkeypatch,
    db_session,
    organization_id,
) -> None:
    execution, auth = _start_closure(db_session, organization_id)
    planner, repository, _, _, _ = _planner(db_session)
    original = repository.list_scoped_ids
    failed = False

    def fail_once(**kwargs):
        nonlocal failed
        if not failed:
            failed = True
            raise RuntimeError("transient planning read failure")
        return original(**kwargs)

    monkeypatch.setattr(repository, "list_scoped_ids", fail_once)
    with pytest.raises(ClosureExportPlanningError):
        planner.plan(
            organization_id=organization_id,
            execution_id=execution.id,
            auth=auth,
            access_token="token",
        )

    count = db_session.scalar(
        select(func.count()).select_from(OrganizationClosureExportPlanModel)
    )
    assert count == 0

    monkeypatch.setattr(repository, "list_scoped_ids", original)
    plan = planner.plan(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )
    assert plan.status == "planned"


def test_cross_organization_execution_cannot_satisfy_plan_lookup(
    db_session,
    organization_id,
    other_organization_id,
) -> None:
    execution, auth = _start_closure(db_session, organization_id)
    planner, _, _, _, _ = _planner(db_session)
    planner.plan(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )

    foreign_auth = _auth(other_organization_id)
    with pytest.raises(ClosureExportPlanNotFoundError):
        planner.get(
            organization_id=other_organization_id,
            execution_id=execution.id,
            auth=foreign_auth,
            access_token="token",
        )


def test_plan_requires_system_authority_and_live_suspension(
    db_session,
    organization_id,
) -> None:
    execution, auth = _start_closure(db_session, organization_id)

    denied, _, _, _, _ = _planner(db_session, allowed=False)
    with pytest.raises(ClosurePermissionDeniedError):
        denied.plan(
            organization_id=organization_id,
            execution_id=execution.id,
            auth=auth,
            access_token="token",
        )

    active, _, _, _, _ = _planner(db_session, lifecycle_status="active")
    with pytest.raises(ClosureLifecyclePreconditionError):
        active.plan(
            organization_id=organization_id,
            execution_id=execution.id,
            auth=auth,
            access_token="token",
        )


def test_api_surface_is_metadata_only_and_has_no_download_or_package_route() -> None:
    paths = create_app().openapi()["paths"]
    plan_path = (
        "/api/v1/system-admin/organizations/{organization_id}/"
        "closure-executions/{execution_id}/export-plan"
    )
    assert plan_path in paths
    assert {"get", "post"} <= set(paths[plan_path])

    closure_paths = [path for path in paths if "closure-executions" in path]
    assert all("download" not in path for path in closure_paths)
    assert all("package" not in path for path in closure_paths)
