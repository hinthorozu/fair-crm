from datetime import UTC, datetime
from uuid import uuid4

from app.modules.customers.domain.value_objects import CustomerStatus, CustomerType
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.imports.application.enrichment_import_matching import apply_enrichment_customer_id_matches
from app.modules.imports.application.import_row_builder import ValidatedRow
from app.modules.imports.domain.value_objects import ImportRowStatus, ImportSuggestedAction
from app.modules.customers.infrastructure.repositories.customer_repository import SqlAlchemyCustomerRepository
from app.modules.scraper.domain.enrichment_adapter import MATCH_REASON_ENRICHMENT_CUSTOMER_ID


def _seed_customer(db_session, organization_id):
    now = datetime.now(tz=UTC)
    customer = CustomerModel(
        id=uuid4(),
        organization_id=organization_id,
        display_name="Enrichment Target",
        normalized_name="enrichment target",
        customer_type=CustomerType.LEAD.value,
        status=CustomerStatus.ACTIVE.value,
        source="manual",
        created_at=now,
        updated_at=now,
    )
    db_session.add(customer)
    db_session.commit()
    return customer


def test_apply_enrichment_customer_id_matches_binds_existing_customer(db_session, organization_id):
    customer = _seed_customer(db_session, organization_id)
    validated = ValidatedRow(
        row_number=1,
        raw={"external_id": str(customer.id)},
        normalized={
            "company_name": customer.display_name,
            "normalized_company_name": customer.normalized_name,
            "external_id": str(customer.id),
            "email": "info@example.com",
        },
        errors=[],
        status=ImportRowStatus.VALID,
    )

    matched = apply_enrichment_customer_id_matches(
        validated_rows=[validated],
        organization_id=organization_id,
        customer_repository=SqlAlchemyCustomerRepository(db_session),
    )

    _, match_fields = matched[0]
    assert match_fields["match_customer_id"] == customer.id
    assert match_fields["match_reason"] == MATCH_REASON_ENRICHMENT_CUSTOMER_ID
    assert match_fields["status"] == ImportRowStatus.READY_TO_UPDATE
    assert match_fields["suggested_action"] == ImportSuggestedAction.LINK_EXISTING_CUSTOMER_TO_FAIR
