"""System fair ids are readable on child workflows. Another organization's fair is not."""

from datetime import UTC, datetime
from io import BytesIO
from uuid import uuid4

import pytest
from openpyxl import Workbook

from app.integrations.kyrox_core.dev_bypass import AllowAllAuthorizationAdapter, NoOpAuditAdapter
from app.modules.customers.application.customer_field_grouping import analyze_customer_groups_by_field
from app.modules.customers.application.export_customers import _load_fair_names_by_customer
from app.modules.customers.infrastructure.persistence.communication_models import CustomerWebsiteModel
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.fairs.application.run_fair_enrichment import RunFairEnrichmentCommand, RunFairEnrichmentUseCase
from app.modules.fairs.domain.entities import Fair
from app.modules.fairs.domain.exceptions import FairEnrichmentNoCandidatesError, FairNotFoundError
from app.modules.fairs.domain.services.normalizers import compute_normalized_name
from app.modules.fairs.domain.value_objects import FairStatus
from app.modules.fairs.infrastructure.repositories.fair_repository import SqlAlchemyFairRepository
from app.modules.fair_emails.application.commands import PreviewRecipientsQuery
from app.modules.fair_emails.application.preview_recipients import PreviewFairEmailRecipientsUseCase
from app.modules.fair_emails.domain.value_objects import RecipientOptions, RecipientPreviewResult
from app.modules.imports.application.batch_display_metadata import build_fair_name_lookup, resolve_fair_name
from app.modules.imports.application.commands import UploadRawImportCommand
from app.modules.imports.application.upload_raw_import import UploadRawImportUseCase
from app.modules.imports.domain.exceptions import InvalidCanonicalImportError
from app.modules.operations.application.create_operation import CreateOperationUseCase
from app.modules.operations.domain.exceptions import InvalidOperationConfigError
from app.modules.participations.infrastructure.persistence.models import CustomerFairParticipationModel
from app.modules.scraper.application.fair_scraper_import_automation import (
    create_and_analyze_import_batch_from_handoff,
)
from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportHandoff
from app.modules.todos.application.validators import ensure_source_fair_exists


def _system_fair(name: str = "System Catalog Fair") -> Fair:
    now = datetime.now(tz=UTC)
    return Fair(
        id=uuid4(),
        organization_id=None,
        name=name,
        organizer=None,
        venue=None,
        city=None,
        country="Türkiye",
        start_date=None,
        end_date=None,
        website=None,
        status=FairStatus.PLANNED,
        description=None,
        normalized_name=compute_normalized_name(name=name),
        created_at=now,
        updated_at=now,
        deleted_at=None,
        origin="system",
        source="tobb",
        external_id=f"2026:{uuid4().hex[:8]}",
    )


def _org_fair(organization_id, name: str) -> Fair:
    now = datetime.now(tz=UTC)
    return Fair(
        id=uuid4(),
        organization_id=organization_id,
        name=name,
        organizer=None,
        venue=None,
        city=None,
        country="Türkiye",
        start_date=None,
        end_date=None,
        website=None,
        status=FairStatus.PLANNED,
        description=None,
        normalized_name=compute_normalized_name(name=name),
        created_at=now,
        updated_at=now,
        deleted_at=None,
        origin="organization",
        source=None,
        external_id=None,
    )


def _customer(db_session, organization_id, name: str) -> CustomerModel:
    now = datetime.now(tz=UTC)
    row = CustomerModel(
        id=uuid4(),
        organization_id=organization_id,
        display_name=name,
        normalized_name=name.lower(),
        customer_type="lead",
        status="active",
        source="manual",
        created_at=now,
        updated_at=now,
    )
    db_session.add(row)
    db_session.flush()
    return row


def _participation(db_session, organization_id, customer_id, fair_id) -> None:
    now = datetime.now(tz=UTC)
    db_session.add(
        CustomerFairParticipationModel(
            id=uuid4(),
            organization_id=organization_id,
            customer_id=customer_id,
            fair_id=fair_id,
            participation_status="exhibitor",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
    )
    db_session.flush()


def test_source_fair_validator_accepts_own_and_system_fairs(
    db_session, organization_id, other_organization_id
):
    repo = SqlAlchemyFairRepository(db_session)
    own = repo.add(_org_fair(organization_id, "Own Fair"))
    system = repo.add(_system_fair())
    other = repo.add(_org_fair(other_organization_id, "Other Fair"))

    ensure_source_fair_exists(repo, organization_id, own.id)
    ensure_source_fair_exists(repo, organization_id, system.id)
    with pytest.raises(FairNotFoundError, match="Fair not found"):
        ensure_source_fair_exists(repo, organization_id, other.id)


def test_todo_create_and_update_accept_system_fair(
    client, auth_headers, db_session, organization_id, other_organization_id
):
    repo = SqlAlchemyFairRepository(db_session)
    own = repo.add(_org_fair(organization_id, "Own Fair"))
    system = repo.add(_system_fair("5. TESBIH VE DOGAL TASLAR 2026 FUARI"))
    other = repo.add(_org_fair(other_organization_id, "Other Fair"))
    db_session.flush()

    created = client.post(
        "/api/v1/todos",
        headers=auth_headers,
        json={"title": "System fair task", "source_fair_id": str(system.id)},
    )
    assert created.status_code == 201, created.text
    assert created.json()["source_fair_id"] == str(system.id)

    updated = client.patch(
        f"/api/v1/todos/{created.json()['id']}",
        headers=auth_headers,
        json={"source_fair_id": str(own.id)},
    )
    assert updated.status_code == 200, updated.text

    switched = client.patch(
        f"/api/v1/todos/{created.json()['id']}",
        headers=auth_headers,
        json={"source_fair_id": str(system.id)},
    )
    assert switched.status_code == 200, switched.text

    foreign = client.post(
        "/api/v1/todos",
        headers=auth_headers,
        json={"title": "Foreign fair task", "source_fair_id": str(other.id)},
    )
    assert foreign.status_code == 404
    assert foreign.json()["detail"] == "Fair not found"


def test_quote_render_shows_system_fair_name(
    client, auth_headers, db_session, organization_id, other_organization_id
):
    repo = SqlAlchemyFairRepository(db_session)
    system = repo.add(_system_fair("System Quote Fair"))
    other = repo.add(_org_fair(other_organization_id, "Hidden Fair"))
    db_session.flush()

    customer = client.post(
        "/api/v1/customers",
        headers=auth_headers,
        json={"display_name": "Beysan", "status": "active"},
    )
    assert customer.status_code == 201, customer.text
    todo = client.post(
        "/api/v1/todos",
        headers=auth_headers,
        json={
            "title": "Beysan teklif",
            "category": "teklif",
            "customer_id": customer.json()["id"],
            "source_fair_id": str(system.id),
        },
    )
    assert todo.status_code == 201, todo.text
    template = client.post(
        "/api/v1/quote-templates",
        headers=auth_headers,
        json={
            "name": "Fiyat",
            "logo_url": None,
            "source_code": "<div>{{fair_name}}</div>",
        },
    )
    assert template.status_code == 201, template.text
    quote = client.post(
        f"/api/v1/quotes/todo/{todo.json()['id']}",
        headers=auth_headers,
        json={
            "template_id": template.json()["id"],
            "quote_date": "2026-10-08",
            "status": "draft",
            "selected_items": [],
        },
    )
    assert quote.status_code == 201, quote.text
    rendered = client.get(f"/api/v1/quotes/todo/{todo.json()['id']}/render", headers=auth_headers)
    assert rendered.status_code == 200, rendered.text
    assert "System Quote Fair" in rendered.json()["html"]

    from uuid import UUID

    from app.modules.quotes.infrastructure.models import QuoteModel

    stored = db_session.get(QuoteModel, UUID(quote.json()["id"]))
    stored.fair_id = other.id
    db_session.flush()
    hidden = client.get(f"/api/v1/quotes/todo/{todo.json()['id']}/render", headers=auth_headers)
    assert hidden.status_code == 404
    assert "Hidden Fair" not in hidden.text


def test_import_name_lookup_and_upload_keep_batch_in_current_organization(
    db_session, organization_id, other_organization_id, user_id
):
    repo = SqlAlchemyFairRepository(db_session)
    own = repo.add(_org_fair(organization_id, "Own Import Fair"))
    system = repo.add(_system_fair("System Import Fair"))
    other = repo.add(_org_fair(other_organization_id, "Other Import Fair"))

    assert resolve_fair_name(repo, organization_id=organization_id, fair_id=own.id) == "Own Import Fair"
    assert resolve_fair_name(repo, organization_id=organization_id, fair_id=system.id) == "System Import Fair"
    assert resolve_fair_name(repo, organization_id=organization_id, fair_id=other.id) is None
    names = build_fair_name_lookup(
        repo, organization_id=organization_id, fair_ids={own.id, system.id, other.id}
    )
    assert names == {own.id: "Own Import Fair", system.id: "System Import Fair"}

    workbook = Workbook()
    workbook.active.append(["company"])
    workbook.active.append(["Beysan"])
    buffer = BytesIO()
    workbook.save(buffer)
    saved_orgs: list = []

    class _Batches:
        def add(self, batch):
            saved_orgs.append(batch.organization_id)
            return batch

    use_case = UploadRawImportUseCase(_Batches(), repo, AllowAllAuthorizationAdapter(), NoOpAuditAdapter())

    def upload(fair_id):
        return use_case.execute(
            UploadRawImportCommand(
                organization_id=organization_id,
                user_id=user_id,
                access_token="token",
                fair_id=fair_id,
                file_name="rows.xlsx",
                file_content=buffer.getvalue(),
            )
        )

    own_result = upload(own.id)
    system_result = upload(system.id)
    assert own_result.fair_id == own.id
    assert system_result.fair_id == system.id
    assert saved_orgs == [organization_id, organization_id]
    with pytest.raises(FairNotFoundError):
        upload(other.id)


def test_scraper_import_automation_accepts_system_fair_without_sharing_the_batch(
    db_session, organization_id, other_organization_id, user_id
):
    repo = SqlAlchemyFairRepository(db_session)
    system = repo.add(_system_fair())
    other = repo.add(_org_fair(other_organization_id, "Other Fair"))
    handoff = ScraperImportHandoff(canonical_rows=[{"company_name": "Beysan"}])

    with pytest.raises(InvalidCanonicalImportError, match="Fair not found"):
        create_and_analyze_import_batch_from_handoff(
            db_session,
            organization_id=organization_id,
            fair_id=other.id,
            run_id=uuid4(),
            handoff=handoff,
            adapter_key="generic",
            source_url="https://example.test",
            user_id=user_id,
        )

    try:
        create_and_analyze_import_batch_from_handoff(
            db_session,
            organization_id=organization_id,
            fair_id=system.id,
            run_id=uuid4(),
            handoff=handoff,
            adapter_key="generic",
            source_url="https://example.test",
            user_id=user_id,
        )
    except InvalidCanonicalImportError as exc:
        assert "Fair not found" not in str(exc)


def test_operation_fair_check_accepts_system_fair(db_session, organization_id, other_organization_id):
    repo = SqlAlchemyFairRepository(db_session)
    own = repo.add(_org_fair(organization_id, "Own Fair"))
    system = repo.add(_system_fair())
    other = repo.add(_org_fair(other_organization_id, "Other Fair"))
    use_case = CreateOperationUseCase(None, None, None, None, None, fair_repository=repo)

    use_case._ensure_fairs_exist(organization_id, [own.id])
    use_case._ensure_fairs_exist(organization_id, [system.id])
    with pytest.raises(InvalidOperationConfigError, match="existing fair"):
        use_case._ensure_fairs_exist(organization_id, [other.id])


def test_enrichment_on_system_fair_stays_inside_the_current_organization(
    db_session, organization_id, other_organization_id
):
    repo = SqlAlchemyFairRepository(db_session)
    system = repo.add(_system_fair())
    other_fair = repo.add(_org_fair(other_organization_id, "Other Fair"))
    own_customer = _customer(db_session, organization_id, "Own Customer")
    foreign_customer = _customer(db_session, other_organization_id, "Foreign Customer")
    _participation(db_session, organization_id, own_customer.id, system.id)
    _participation(db_session, other_organization_id, foreign_customer.id, system.id)
    now = datetime.now(tz=UTC)
    for org, customer in ((organization_id, own_customer), (other_organization_id, foreign_customer)):
        db_session.add(
            CustomerWebsiteModel(
                id=uuid4(),
                organization_id=org,
                customer_id=customer.id,
                website="https://example.test",
                is_primary=True,
                created_at=now,
            )
        )
    db_session.flush()

    class _History:
        def start_run(self, **kwargs):
            self.kwargs = kwargs
            return None

    history = _History()
    use_case = RunFairEnrichmentUseCase(repo, history, db_session)
    use_case.execute(
        RunFairEnrichmentCommand(
            organization_id=organization_id,
            fair_id=system.id,
            include_existing_email=True,
        )
    )
    assert history.kwargs["organization_id"] == organization_id
    assert history.kwargs["fair_id"] == system.id
    assert history.kwargs["organization_id"] is not None

    with pytest.raises(FairNotFoundError):
        use_case.execute(
            RunFairEnrichmentCommand(organization_id=organization_id, fair_id=other_fair.id)
        )
    with pytest.raises(FairEnrichmentNoCandidatesError):
        use_case.execute(
            RunFairEnrichmentCommand(
                organization_id=organization_id,
                fair_id=repo.add(_org_fair(organization_id, "Empty Own Fair")).id,
                include_existing_email=True,
            )
        )


def test_recipient_preview_uses_visible_fair_and_current_organization(
    db_session, organization_id, other_organization_id, user_id
):
    repo = SqlAlchemyFairRepository(db_session)
    own = repo.add(_org_fair(organization_id, "Own Fair"))
    system = repo.add(_system_fair())
    other = repo.add(_org_fair(other_organization_id, "Other Fair"))
    seen: list = []

    class _Recipients:
        def preview(self, organization_id, fair_id, options):
            seen.append((organization_id, fair_id))
            return RecipientPreviewResult(0, 0, 0, 0, 0, [])

    use_case = PreviewFairEmailRecipientsUseCase(repo, _Recipients(), AllowAllAuthorizationAdapter())

    def preview(fair_id):
        return use_case.execute(
            PreviewRecipientsQuery(
                organization_id=organization_id,
                fair_id=fair_id,
                access_token="token",
                user_id=user_id,
                recipient_options=RecipientOptions(),
            )
        )

    preview(own.id)
    preview(system.id)
    assert seen == [(organization_id, own.id), (organization_id, system.id)]
    with pytest.raises(FairNotFoundError):
        preview(other.id)


def test_grouping_and_export_keep_system_fair_names_inside_the_organization(
    db_session, organization_id, other_organization_id
):
    repo = SqlAlchemyFairRepository(db_session)
    own = repo.add(_org_fair(organization_id, "Own Fair"))
    system = repo.add(_system_fair("System Export Fair"))
    other = repo.add(_org_fair(other_organization_id, "Other Fair"))
    own_customer = _customer(db_session, organization_id, "Own Customer")
    foreign_customer = _customer(db_session, other_organization_id, "Foreign Customer")
    _participation(db_session, organization_id, own_customer.id, system.id)
    _participation(db_session, other_organization_id, foreign_customer.id, system.id)

    names = _load_fair_names_by_customer(db_session, organization_id, [own_customer.id, foreign_customer.id])
    assert names[own_customer.id] == ["System Export Fair"]
    assert foreign_customer.id not in names

    def grouped(fair_id):
        try:
            analyze_customer_groups_by_field(
                db_session,
                organization_id=organization_id,
                group_by="company_name",
                fair_id=fair_id,
            )
        except ValueError:
            raise
        except Exception as exc:
            return exc

    assert not isinstance(grouped(own.id), ValueError)
    assert not isinstance(grouped(system.id), ValueError)
    with pytest.raises(ValueError, match="Fair not found"):
        grouped(other.id)
