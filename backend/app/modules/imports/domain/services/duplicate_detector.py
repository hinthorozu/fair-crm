from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from uuid import UUID

from app.modules.customers.domain.entities import Customer
from app.modules.imports.domain.services.company_name_matcher import (
    MATCH_SCORE_MIN,
    MATCH_SCORE_POSSIBLE,
    MATCH_SCORE_STRONG,
    format_match_explanation,
    score_company_name_pair,
)
from app.modules.imports.domain.services.company_name_normalizer import (
    company_name_comparison_key,
    normalize_import_company_name,
)

MATCH_TYPE_EXACT = "exact_normalized_match"
MATCH_TYPE_FUZZY = "fuzzy_name_candidate"
MATCH_TYPE_WEAK = "weak_name_candidate"
MATCH_TYPE_NO_MATCH = "no_match"

BATCH_DUPLICATE_REASON = "batch_duplicate_company_name"


@dataclass(frozen=True)
class DuplicateMatch:
    customer_id: UUID
    confidence: int
    reason: str
    explanation: str | None = None


def customer_match_key(customer: Customer) -> str:
    return company_name_comparison_key(
        display_name=customer.display_name,
        legal_name=customer.legal_name,
    )


def _reason_for_confidence(confidence: int) -> str:
    if confidence >= MATCH_SCORE_STRONG:
        return MATCH_TYPE_EXACT
    if confidence >= MATCH_SCORE_POSSIBLE:
        return MATCH_TYPE_FUZZY
    return MATCH_TYPE_WEAK


@dataclass
class CustomerMatchIndex:
    """Pre-built exact + prefix-bucketed token match index for import duplicate detection."""

    exact: dict[str, UUID] = field(default_factory=dict)
    _entries: list[tuple[str, str, UUID]] = field(default_factory=list)
    _by_prefix: dict[str, list[int]] = field(default_factory=dict)

    @classmethod
    def build(cls, customers: list[Customer]) -> CustomerMatchIndex:
        exact: dict[str, UUID] = {}
        entries: list[tuple[str, str, UUID]] = []
        by_prefix: dict[str, list[int]] = defaultdict(list)

        for customer in customers:
            keys: set[str] = set()
            display_source = (
                customer.legal_name.strip()
                if customer.legal_name and customer.legal_name.strip()
                else customer.display_name
            )
            match_key = company_name_comparison_key(
                display_name=customer.display_name,
                legal_name=customer.legal_name,
            )
            if match_key:
                keys.add(match_key)
            if customer.normalized_name and customer.normalized_name.strip():
                keys.add(normalize_import_company_name(customer.normalized_name))

            if not keys:
                continue

            primary_key = match_key or next(iter(keys))
            idx = len(entries)
            entries.append((primary_key, display_source, customer.id))
            prefix = primary_key[:3] if len(primary_key) >= 3 else primary_key
            by_prefix[prefix].append(idx)

            for key in keys:
                exact.setdefault(key, customer.id)

        return cls(exact=exact, _entries=entries, _by_prefix=dict(by_prefix))

    def find(self, normalized_company_name: str, *, raw_company_name: str | None = None) -> DuplicateMatch | None:
        if not normalized_company_name:
            return None

        query_display = raw_company_name or normalized_company_name

        exact_id = self.exact.get(normalized_company_name)
        if exact_id is not None:
            return DuplicateMatch(
                customer_id=exact_id,
                confidence=100,
                reason=MATCH_TYPE_EXACT,
                explanation="normalized_exact",
            )

        prefix = normalized_company_name[:3] if len(normalized_company_name) >= 3 else normalized_company_name
        candidate_indices = self._by_prefix.get(prefix)
        if not candidate_indices:
            return None

        best_match: DuplicateMatch | None = None
        best_confidence = 0
        query_len = len(normalized_company_name)

        for idx in candidate_indices:
            key, display_name, customer_id = self._entries[idx]
            if abs(len(key) - query_len) > max(12, int(query_len * 0.75)):
                continue

            scored = score_company_name_pair(query_display, display_name)
            if scored is None or scored.confidence <= best_confidence:
                continue

            best_confidence = scored.confidence
            best_match = DuplicateMatch(
                customer_id=customer_id,
                confidence=scored.confidence,
                reason=_reason_for_confidence(scored.confidence),
                explanation=format_match_explanation(scored.explanations) or None,
            )

        if best_match is None or best_confidence < MATCH_SCORE_MIN:
            return None
        return best_match


def find_customer_match(
    normalized_company_name: str,
    customers: list[Customer] | CustomerMatchIndex,
    *,
    raw_company_name: str | None = None,
) -> DuplicateMatch | None:
    if isinstance(customers, CustomerMatchIndex):
        return customers.find(normalized_company_name, raw_company_name=raw_company_name)
    return CustomerMatchIndex.build(customers).find(
        normalized_company_name, raw_company_name=raw_company_name
    )
