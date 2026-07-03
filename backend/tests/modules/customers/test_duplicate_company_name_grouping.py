from datetime import UTC, datetime
from uuid import uuid4

from app.modules.customers.application.duplicate_company_name_grouping import (
    merge_similar_company_name_buckets,
)
from app.modules.customers.domain.value_objects import CustomerStatus, CustomerType
from app.modules.customers.infrastructure.persistence.models import CustomerModel


def _model(display_name: str, *, legal_name: str | None = None) -> CustomerModel:
    now = datetime.now(tz=UTC)
    return CustomerModel(
        id=uuid4(),
        organization_id=uuid4(),
        display_name=display_name,
        legal_name=legal_name,
        normalized_name=display_name.lower(),
        customer_type=CustomerType.LEAD.value,
        status=CustomerStatus.ACTIVE.value,
        source="manual",
        created_at=now,
        updated_at=now,
    )


def test_merge_similar_company_name_buckets_unions_probable_matches():
    first = _model("ABC GIDA LTD")
    second = _model("ABC GIDA LIMITED SIRKETI")
    buckets = {
        "ABC GIDA": {first.id: first},
        "ABC GIDA LIMITED": {second.id: second},
    }

    merged = merge_similar_company_name_buckets(buckets)

    assert len(merged) == 1
    only_group = next(iter(merged.values()))
    assert {first.id, second.id} == set(only_group.keys())
