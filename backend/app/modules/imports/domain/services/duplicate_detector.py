from dataclasses import dataclass
from difflib import SequenceMatcher
from uuid import UUID

from app.modules.customers.domain.entities import Customer
from app.modules.imports.domain.services.company_name_normalizer import normalize_import_company_name


@dataclass(frozen=True)
class DuplicateMatch:
    customer_id: UUID
    confidence: int
    reason: str


EXACT_REASON = "Exact normalized company name match"
FUZZY_STRONG_REASON = "Strong fuzzy company name match"
FUZZY_POSSIBLE_REASON = "Possible fuzzy company name match"
BATCH_DUPLICATE_REASON = "Duplicate normalized company name within batch"


def customer_match_key(customer: Customer) -> str:
    source = customer.legal_name.strip() if customer.legal_name and customer.legal_name.strip() else customer.display_name
    return normalize_import_company_name(source)


def find_customer_match(
    normalized_company_name: str,
    customers: list[Customer],
) -> DuplicateMatch | None:
    if not normalized_company_name:
        return None

    for customer in customers:
        key = customer_match_key(customer)
        if key == normalized_company_name:
            return DuplicateMatch(
                customer_id=customer.id,
                confidence=100,
                reason=EXACT_REASON,
            )

    best_match: DuplicateMatch | None = None
    best_score = 0.0

    for customer in customers:
        key = customer_match_key(customer)
        if not key:
            continue
        score = SequenceMatcher(None, normalized_company_name, key).ratio() * 100
        if score > best_score:
            best_score = score
            if score >= 90:
                reason = FUZZY_STRONG_REASON
            elif score >= 75:
                reason = FUZZY_POSSIBLE_REASON
            else:
                continue
            best_match = DuplicateMatch(
                customer_id=customer.id,
                confidence=int(round(score)),
                reason=reason,
            )

    return best_match
