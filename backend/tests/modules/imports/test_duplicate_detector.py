"""Tests for indexed import duplicate detection."""

import time
from datetime import UTC, datetime
from uuid import uuid4

from app.modules.customers.domain.entities import Customer
from app.modules.customers.domain.value_objects import CustomerSource, CustomerStatus, CustomerType
from app.modules.imports.domain.services.company_name_normalizer import normalize_import_company_name
from app.modules.imports.domain.services.duplicate_detector import (
    MATCH_TYPE_EXACT,
    MATCH_TYPE_FUZZY,
    CustomerMatchIndex,
    customer_match_key,
    find_customer_match,
)


def _customer(display_name: str, *, legal_name: str | None = None) -> Customer:
    now = datetime.now(tz=UTC)
    return Customer.create(
        organization_id=uuid4(),
        display_name=display_name,
        legal_name=legal_name,
        customer_type=CustomerType.LEAD,
        status=CustomerStatus.ACTIVE,
        source=CustomerSource.MANUAL,
        now=now,
    )


def test_exact_match_uses_index():
    customer = _customer("Acme Ltd")
    index = CustomerMatchIndex.build([customer])
    key = customer_match_key(customer)
    match = index.find(key)
    assert match is not None
    assert match.customer_id == customer.id
    assert match.confidence == 100
    assert match.reason == MATCH_TYPE_EXACT


def test_fuzzy_match_within_prefix_bucket():
    customer = _customer("Celik Makina Imalat")
    index = CustomerMatchIndex.build([customer])
    query = normalize_import_company_name("Celik Makina Iml")
    match = index.find(query)
    assert match is not None
    assert match.customer_id == customer.id
    assert match.confidence >= 85
    assert match.reason == MATCH_TYPE_FUZZY


def test_fuzzy_below_threshold_returns_none():
    customer = _customer("Totally Different Company Name Ltd")
    index = CustomerMatchIndex.build([customer])
    match = index.find(normalize_import_company_name("XYZ Corp"))
    assert match is None


def test_index_scales_better_than_naive_scan():
    customers = [_customer(f"Prefix Company {i:05d}") for i in range(2000)]
    customers.append(_customer("ABC Makina Sanayi A.Ş."))
    index = CustomerMatchIndex.build(customers)

    started = time.perf_counter()
    for _ in range(100):
        index.find(normalize_import_company_name("ABC Makina"))
    elapsed = time.perf_counter() - started

    assert elapsed < 2.0


def test_find_customer_match_accepts_customer_list():
    customer = _customer("Exact Match Co")
    match = find_customer_match(customer_match_key(customer), [customer])
    assert match is not None
    assert match.customer_id == customer.id
