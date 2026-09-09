from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
from zipfile import ZipFile

import pytest
from sqlalchemy import delete, select

from app.integrations.kyrox_core.ports import AuthContext
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.email_accounts.infrastructure.persistence.models import (
    EmailAccountModel,
    EmailAccountSmtpConfigModel,
)
from app.modules.imports.infrastructure.persistence.models import ImportBatchModel
from app.modules.organization_closure.application.closure_package import (
    PACKAGE_RETENTION_DAYS,
    STATUS_BLOCKED,
    STATUS_INTEGRITY_VERIFIED,
    OrganizationClosurePackageService,
)
from app.modules.organization_closure.application.export_planner import (
    OrganizationClosureExportPlanner,
)
from app.modules.organization_closure.application.service import (
    ClosureExecutionConflictError,
    ClosureLifecyclePreconditionError,
    OrganizationClosureService,
)
from app.modules.organization_closure.infrastructure.export_plan_repository import (
    SqlAlchemyOrganizationClosureExportPlanRepository,
)
from app.modules.organization_closure.infrastructure.models import (
    OrganizationClosureArtifactInventoryModel,
    OrganizationClosurePackageModel,
)
from app.modules.organization_closure.infrastructure.package_repository import (
    SqlAlchemyOrganizationClosurePackageRepository,
)
from app.modules.organization_closure.infrastructure.package_storage import (
    inspect_package,
    resolve_stored_locator,
)
from app.modules.organization_closure.infrastructure.repository import (
    SqlAlchemyOrganizationClosureRepository,
)
from app.modules.quote_templates.infrastructure.logo_storage import LOGO_API_PREFIX
from app.modules.quote_templates.infrastructure.models import (
    QuoteTemplateModel,
    QuoteTemplateVersionModel,
)
from app.modules.scraper.infrastructure.persistence.models import ScraperRunHistoryModel


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

    def get_snapshot(self, organization_id: object) -> SimpleNamespace:
        _ = organization_id
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
        idempotency_key=f"ol08-e1-{uuid4()}",
        auth=auth,
        access_token="token",
    )
    db_session.flush()
    return execution, auth


def _plan(db_session, organization_id, execution, auth):
    planner = OrganizationClosureExportPlanner(
        SqlAlchemyOrganizationClosureExportPlanRepository(db_session),
        FakeAuthorization(),
        FakeLifecycle(),
        RecordingAudit(),
    )
    plan = planner.plan(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )
    db_session.flush()
    return plan


def _service(
    db_session,
    tmp_path: Path,
    *,
    lifecycle: FakeLifecycle | None = None,
):
    audit = RecordingAudit()
    package_root = tmp_path / "packages"
    logo_root = tmp_path / "logos"
    handoff_root = tmp_path / "handoff"
    service = OrganizationClosurePackageService(
        SqlAlchemyOrganizationClosurePackageRepository(db_session),
        FakeAuthorization(),
        lifecycle or FakeLifecycle(),
        audit,
        package_storage_root=package_root,
        logo_storage_root=logo_root,
        handoff_storage_root=handoff_root,
    )
    return service, audit, package_root, logo_root, handoff_root


def _customer(organization_id, *, name: str = "Closure Package Customer"):
    now = datetime.now(tz=UTC)
    return CustomerModel(
        id=uuid4(),
        organization_id=organization_id,
        display_name=name,
        legal_name=None,
        trade_name=None,
        normalized_name=f"closure-package-{uuid4()}",
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


def _add_import_upload(db_session, organization_id, *, content: bytes) -> ImportBatchModel:
    now = datetime.now(tz=UTC)
    batch = ImportBatchModel(
        id=uuid4(),
        organization_id=organization_id,
        fair_id=None,
        source_type="excel",
        file_name="customers.xlsx",
        status="completed",
        total_rows=1,
        valid_rows=1,
        invalid_rows=0,
        duplicate_rows=0,
        created_rows=1,
        updated_rows=0,
        skipped_rows=0,
        created_participations=0,
        updated_participations=0,
        column_mapping_json={},
        raw_preview_json={},
        has_header_row=True,
        header_mode="first_row",
        header_row_index=0,
        selected_sheet_name="Sheet1",
        stored_file_content=content,
        created_at=now,
        updated_at=now,
        completed_at=now,
        analyzed_at=now,
        notes=None,
    )
    db_session.add(batch)
    db_session.flush()
    return batch


def _add_managed_logo(
    db_session,
    organization_id,
    logo_root: Path,
    *,
    content: bytes,
) -> tuple[QuoteTemplateVersionModel, str]:
    now = datetime.now(tz=UTC)
    template = QuoteTemplateModel(
        id=uuid4(),
        organization_id=organization_id,
        name="Closure Package Template",
        current_version_id=None,
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )
    db_session.add(template)
    db_session.flush()
    filename = f"{uuid4().hex}.png"
    organization_dir = logo_root / str(organization_id)
    organization_dir.mkdir(parents=True, exist_ok=True)
    (organization_dir / filename).write_bytes(content)
    version = QuoteTemplateVersionModel(
        id=uuid4(),
        template_id=template.id,
        version_number=1,
        logo_url=f"{LOGO_API_PREFIX}{organization_id}/{filename}",
        source_code="<html>portable quote template</html>",
        created_at=now,
        created_by=uuid4(),
    )
    db_session.add(version)
    db_session.flush()
    template.current_version_id = version.id
    db_session.flush()
    return version, filename


def _add_external_logo(db_session, organization_id) -> QuoteTemplateVersionModel:
    now = datetime.now(tz=UTC)
    template = QuoteTemplateModel(
        id=uuid4(),
        organization_id=organization_id,
        name="External Logo Template",
        current_version_id=None,
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )
    db_session.add(template)
    db_session.flush()
    version = QuoteTemplateVersionModel(
        id=uuid4(),
        template_id=template.id,
        version_number=1,
        logo_url="https://example.invalid/external-logo.png",
        source_code="<html>external logo reference</html>",
        created_at=now,
        created_by=uuid4(),
    )
    db_session.add(version)
    db_session.flush()
    template.current_version_id = version.id
    db_session.flush()
    return version


def _add_scraper_handoff(
    db_session,
    organization_id,
    handoff_root: Path,
    *,
    content: bytes,
) -> ScraperRunHistoryModel:
    now = datetime.now(tz=UTC)
    run_id = uuid4()
    handoff_root.mkdir(parents=True, exist_ok=True)
    path = handoff_root / f"{run_id}.json"
    path.write_bytes(content)
    run = ScraperRunHistoryModel(
        id=run_id,
        adapter_key="test-adapter",
        status="completed",
        started_at=now,
        finished_at=now,
        duration_ms=10,
        organization_id=organization_id,
        fair_id=None,
        input_url="https://example.invalid/fair",
        fair_name="Example Fair",
        fair_year=2026,
        total_rows=1,
        website_count=1,
        email_count=0,
        phone_count=0,
        instagram_count=0,
        linkedin_count=0,
        facebook_count=0,
        youtube_count=0,
        x_count=0,
        error_message=None,
        output_json_path=str(path),
        output_excel_path=None,
        run_source="manual_test",
        import_batch_id=None,
        cancel_requested_by=None,
        cancel_requested_at=None,
        last_heartbeat_at=now,
        progress_current=1,
        progress_total=1,
    )
    db_session.add(run)
    db_session.flush()
    return run


def test_required_package_materializes_structured_data_registered_artifacts_and_integrity(
    db_session,
    organization_id,
    tmp_path,
) -> None:
    execution, auth = _start_closure(db_session, organization_id)
    service, audit, package_root, logo_root, handoff_root = _service(
        db_session,
        tmp_path,
    )
    customer = _customer(organization_id)
    db_session.add(customer)
    import_bytes = b"ORIGINAL-IMPORT-BYTES"
    logo_bytes = b"\x89PNG\r\nclosure-logo"
    handoff_bytes = b'{"portable":"scraper-handoff"}\n'
    import_batch = _add_import_upload(db_session, organization_id, content=import_bytes)
    logo_version, logo_filename = _add_managed_logo(
        db_session,
        organization_id,
        logo_root,
        content=logo_bytes,
    )
    scraper_run = _add_scraper_handoff(
        db_session,
        organization_id,
        handoff_root,
        content=handoff_bytes,
    )
    external_version = _add_external_logo(db_session, organization_id)
    db_session.flush()
    _plan(db_session, organization_id, execution, auth)

    package = service.generate(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )

    assert package.status == STATUS_INTEGRITY_VERIFIED
    assert package.package_digest is not None
    assert package.byte_size and package.byte_size > 0
    assert package.ready_at is not None
    assert package.integrity_verified_at is not None
    assert package.expires_at == package.ready_at + timedelta(days=PACKAGE_RETENTION_DAYS)
    assert package.manifest_json["organization_id"] == str(organization_id)
    assert package.manifest_json["closure_execution_id"] == str(execution.id)
    assert package.manifest_json["integrity"]["secret_exclusion"] == "enforced"

    archive_path = resolve_stored_locator(
        package.storage_locator,
        storage_root=package_root,
    )
    inspected = inspect_package(archive_path)
    assert inspected.package_digest == package.package_digest
    assert inspected.manifest_digest == package.manifest_digest

    with ZipFile(archive_path, "r") as archive:
        names = set(archive.namelist())
        assert "manifest.json" in names
        assert "structured/customers/customers.json" in names
        assert f"artifacts/quote-template-logos/{logo_filename}" in names
        assert f"artifacts/import-uploads/{import_batch.id}/original-upload.bin" in names
        assert any(
            name.startswith(f"artifacts/scraper-handoff/{scraper_run.id}/")
            for name in names
        )
        customers = json.loads(
            archive.read("structured/customers/customers.json").decode("utf-8")
        )
        assert customers["records"][0]["id"] == str(customer.id)
        assert archive.read(f"artifacts/quote-template-logos/{logo_filename}") == logo_bytes
        assert (
            archive.read(f"artifacts/import-uploads/{import_batch.id}/original-upload.bin")
            == import_bytes
        )

    repository = SqlAlchemyOrganizationClosurePackageRepository(db_session)
    inventory = repository.list_inventory(organization_id, execution.id, package.id)
    keys = {item.artifact_key for item in inventory}
    assert f"quote_template_logo:{logo_version.id}" in keys
    assert f"import_upload:{import_batch.id}" in keys
    assert any(key.startswith(f"scraper_handoff:{scraper_run.id}:json:") for key in keys)
    external = next(
        item
        for item in inventory
        if item.artifact_key == f"quote_template_logo_external:{external_version.id}"
    )
    assert external.ownership_class == "external_reference"
    assert external.package_entry is None
    assert external.cleanup_action == "relational_pointer_only"
    assert any(
        event.get("action") == "organization_closure.package.integrity_verified"
        for event in audit.events
    )


def test_unreferenced_managed_logo_is_inventoried_but_not_copied_to_package(
    db_session,
    organization_id,
    tmp_path,
) -> None:
    execution, auth = _start_closure(db_session, organization_id)
    service, _, package_root, logo_root, _ = _service(db_session, tmp_path)
    organization_dir = logo_root / str(organization_id)
    organization_dir.mkdir(parents=True, exist_ok=True)
    orphan = organization_dir / "orphan.png"
    orphan.write_bytes(b"orphan-logo")
    _plan(db_session, organization_id, execution, auth)

    package = service.generate(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )

    assert package.status == STATUS_INTEGRITY_VERIFIED
    inventory = SqlAlchemyOrganizationClosurePackageRepository(db_session).list_inventory(
        organization_id,
        execution.id,
        package.id,
    )
    orphan_item = next(item for item in inventory if item.artifact_key == "quote_template_logo_orphan:orphan.png")
    assert orphan_item.package_disposition == "not_included_unreferenced_orphan"
    assert orphan_item.cleanup_action == "hard_delete_after_gate"
    assert orphan_item.package_entry is None
    with ZipFile(
        resolve_stored_locator(package.storage_locator, storage_root=package_root),
        "r",
    ) as archive:
        assert "artifacts/quote-template-logos/orphan.png" not in archive.namelist()


def test_secret_bearing_smtp_material_never_enters_package_or_inventory(
    db_session,
    organization_id,
    tmp_path,
) -> None:
    execution, auth = _start_closure(db_session, organization_id)
    service, audit, package_root, _, _ = _service(db_session, tmp_path)
    now = datetime.now(tz=UTC)
    secret = "OL08-E1-SECRET-SENTINEL"
    account = EmailAccountModel(
        id=uuid4(),
        organization_id=organization_id,
        name="Secret SMTP",
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
    db_session.add(account)
    db_session.flush()
    db_session.add(
        EmailAccountSmtpConfigModel(
            email_account_id=account.id,
            host="smtp.example.com",
            port=587,
            username="sender@example.com",
            password=secret,
            encryption_type="starttls",
        )
    )
    db_session.flush()
    _plan(db_session, organization_id, execution, auth)

    package = service.generate(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )

    archive_path = resolve_stored_locator(package.storage_locator, storage_root=package_root)
    assert secret.encode() not in archive_path.read_bytes()
    durable = json.dumps(package.manifest_json, sort_keys=True) + json.dumps(
        audit.events,
        sort_keys=True,
        default=str,
    )
    assert secret not in durable
    assert "email_account_smtp_configs" not in durable


def test_stale_export_plan_blocks_package_before_any_canonical_archive(
    db_session,
    organization_id,
    tmp_path,
) -> None:
    execution, auth = _start_closure(db_session, organization_id)
    service, _, package_root, _, _ = _service(db_session, tmp_path)
    _plan(db_session, organization_id, execution, auth)
    db_session.add(_customer(organization_id, name="Late customer"))
    db_session.flush()

    package = service.generate(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )

    assert package.status == STATUS_BLOCKED
    assert package.failure_code == "export_plan_stale"
    archive_path = resolve_stored_locator(package.storage_locator, storage_root=package_root)
    assert not archive_path.exists()


def test_recorded_scraper_artifact_outside_handoff_root_fails_closed(
    db_session,
    organization_id,
    tmp_path,
) -> None:
    execution, auth = _start_closure(db_session, organization_id)
    service, _, _, _, handoff_root = _service(db_session, tmp_path)
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    now = datetime.now(tz=UTC)
    run_id = uuid4()
    db_session.add(
        ScraperRunHistoryModel(
            id=run_id,
            adapter_key="test-adapter",
            status="completed",
            started_at=now,
            finished_at=now,
            duration_ms=1,
            organization_id=organization_id,
            fair_id=None,
            input_url=None,
            fair_name=None,
            fair_year=None,
            total_rows=0,
            website_count=0,
            email_count=0,
            phone_count=0,
            instagram_count=0,
            linkedin_count=0,
            facebook_count=0,
            youtube_count=0,
            x_count=0,
            error_message=None,
            output_json_path=str(outside),
            output_excel_path=None,
            run_source="manual_test",
            import_batch_id=None,
            cancel_requested_by=None,
            cancel_requested_at=None,
            last_heartbeat_at=now,
            progress_current=0,
            progress_total=0,
        )
    )
    db_session.flush()
    _plan(db_session, organization_id, execution, auth)

    package = service.generate(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )

    assert handoff_root != outside.parent
    assert package.status == STATUS_BLOCKED
    assert package.failure_code == "unsafe_scraper_handoff_locator"


def test_successful_generation_is_idempotent_and_download_does_not_reset_clock(
    db_session,
    organization_id,
    tmp_path,
) -> None:
    execution, auth = _start_closure(db_session, organization_id)
    service, _, _, _, _ = _service(db_session, tmp_path)
    _plan(db_session, organization_id, execution, auth)

    first = service.generate(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )
    first_ready_at = first.ready_at
    first_expires_at = first.expires_at
    first_digest = first.package_digest
    first_attempts = first.attempt_count

    second = service.generate(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )
    package, path = service.resolve_download(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )

    assert second.id == first.id
    assert second.package_digest == first_digest
    assert second.ready_at == first_ready_at
    assert second.expires_at == first_expires_at
    assert second.attempt_count == first_attempts
    assert package.expires_at == first_expires_at
    assert path.is_file()


def test_existing_canonical_bytes_can_reconcile_after_db_state_loss(
    db_session,
    organization_id,
    tmp_path,
) -> None:
    execution, auth = _start_closure(db_session, organization_id)
    service, _, package_root, _, _ = _service(db_session, tmp_path)
    _plan(db_session, organization_id, execution, auth)
    first = service.generate(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )
    first_digest = first.package_digest
    first_ready_at = first.ready_at
    archive_path = resolve_stored_locator(first.storage_locator, storage_root=package_root)
    assert archive_path.is_file()

    db_session.execute(
        delete(OrganizationClosureArtifactInventoryModel).where(
            OrganizationClosureArtifactInventoryModel.package_id == first.id
        )
    )
    db_session.execute(
        delete(OrganizationClosurePackageModel).where(
            OrganizationClosurePackageModel.id == first.id
        )
    )
    db_session.flush()

    recovered = service.generate(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )

    assert recovered.id == first.id
    assert recovered.status == STATUS_INTEGRITY_VERIFIED
    assert recovered.package_digest == first_digest
    assert recovered.ready_at == first_ready_at
    assert archive_path.is_file()


def test_download_fails_closed_after_expiry_or_reactivation(
    db_session,
    organization_id,
    tmp_path,
) -> None:
    execution, auth = _start_closure(db_session, organization_id)
    suspended = FakeLifecycle(status="suspended")
    service, _, _, _, _ = _service(db_session, tmp_path, lifecycle=suspended)
    _plan(db_session, organization_id, execution, auth)
    package = service.generate(
        organization_id=organization_id,
        execution_id=execution.id,
        auth=auth,
        access_token="token",
    )

    package.expires_at = datetime.now(tz=UTC) - timedelta(seconds=1)
    db_session.flush()
    with pytest.raises(ClosureExecutionConflictError, match="expired"):
        service.resolve_download(
            organization_id=organization_id,
            execution_id=execution.id,
            auth=auth,
            access_token="token",
        )

    package.expires_at = datetime.now(tz=UTC) + timedelta(days=1)
    suspended.status = "active"
    with pytest.raises(ClosureLifecyclePreconditionError):
        service.resolve_download(
            organization_id=organization_id,
            execution_id=execution.id,
            auth=auth,
            access_token="token",
        )


def test_inventory_locator_is_not_exposed_by_api_response_schema() -> None:
    from app.modules.organization_closure.api.schemas import (
        OrganizationClosureArtifactInventoryResponse,
    )

    assert "locator_json" not in OrganizationClosureArtifactInventoryResponse.model_fields
