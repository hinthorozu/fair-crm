"""Company-name fuzzy duplicate grouping — used only by Duplicate Customer Analysis."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from uuid import UUID

from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.imports.domain.services.company_name_matcher import (
    MATCH_SCORE_POSSIBLE,
    format_match_explanation,
    is_short_single_token_hub,
    score_company_name_pair,
)
from app.modules.imports.domain.services.company_name_normalizer import (
    core_tokens,
    normalize_import_company_name,
    tokenize_company_name,
)

_COMPANY_NAME_SIMILARITY_MAX_BLOCK = 32


@dataclass(frozen=True)
class CompanyNameBucketMergeEvent:
    left_bucket_key: str
    right_bucket_key: str
    score: int
    match_type: str
    rule: str


@dataclass(frozen=True)
class CompanyNameBucketMergeResult:
    buckets: dict[str, dict[UUID, CustomerModel]]
    merge_events: tuple[CompanyNameBucketMergeEvent, ...]


def _company_name_block_key(normalized: str) -> str:
    tokens = [token for token in normalized.split() if len(token) > 2]
    if not tokens:
        tokens = [token for token in normalized.split() if token]
    return tokens[0] if tokens else normalized


def _normalized_bucket_tokens(bucket_key: str) -> list[str]:
    normalized = normalize_import_company_name(bucket_key.replace("_", " "))
    if normalized:
        return tokenize_company_name(normalized)
    return tokenize_company_name(bucket_key.lower())


def is_short_hub_bucket_key(bucket_key: str) -> bool:
    """Bucket keyed by a single short token (e.g. ABC, SDK) — fuzzy merge hub candidate."""
    tokens = _normalized_bucket_tokens(bucket_key)
    return is_short_single_token_hub(core_tokens(tokens))


def _customer_company_name_for_grouping(model: CustomerModel) -> str:
    if model.legal_name and model.legal_name.strip():
        return model.legal_name.strip()
    return model.display_name.strip()


def _bucket_is_fuzzy_merge_eligible(bucket_key: str) -> bool:
    if is_short_hub_bucket_key(bucket_key):
        return False
    tokens = _normalized_bucket_tokens(bucket_key)
    core = core_tokens(tokens)
    return not is_short_single_token_hub(core)


def merge_similar_company_name_buckets(
    buckets: dict[str, dict[UUID, CustomerModel]],
) -> CompanyNameBucketMergeResult:
    """Union exact-normalized buckets whose display names score as probable duplicates."""
    if len(buckets) < 2:
        return CompanyNameBucketMergeResult(buckets=buckets, merge_events=())

    keys = sorted(buckets.keys())
    canonical: dict[str, str] = {key: key for key in keys}
    merge_events: list[CompanyNameBucketMergeEvent] = []

    def find(key: str) -> str:
        while canonical[key] != key:
            canonical[key] = canonical[canonical[key]]
            key = canonical[key]
        return key

    def union(left: str, right: str, *, event: CompanyNameBucketMergeEvent) -> None:
        root_left = find(left)
        root_right = find(right)
        if root_left == root_right:
            return
        merge_events.append(event)
        if root_left <= root_right:
            canonical[root_right] = root_left
        else:
            canonical[root_left] = root_right

    block_keys: dict[str, list[str]] = defaultdict(list)
    for key in keys:
        if not _bucket_is_fuzzy_merge_eligible(key):
            continue
        block_keys[_company_name_block_key(normalize_import_company_name(key.lower()) or key.lower())].append(
            key
        )

    for block in block_keys.values():
        if len(block) < 2 or len(block) > _COMPANY_NAME_SIMILARITY_MAX_BLOCK:
            continue
        for index, key_a in enumerate(block):
            if not _bucket_is_fuzzy_merge_eligible(key_a) or len(buckets[key_a]) == 0:
                continue
            representative_a = next(iter(buckets[key_a].values()))
            name_a = _customer_company_name_for_grouping(representative_a)
            for key_b in block[index + 1 :]:
                if key_a == key_b or find(key_a) == find(key_b):
                    continue
                if not _bucket_is_fuzzy_merge_eligible(key_b) or len(buckets[key_b]) == 0:
                    continue
                representative_b = next(iter(buckets[key_b].values()))
                name_b = _customer_company_name_for_grouping(representative_b)
                match = score_company_name_pair(name_a, name_b)
                if match is None or match.confidence < MATCH_SCORE_POSSIBLE:
                    continue
                union(
                    key_a,
                    key_b,
                    event=CompanyNameBucketMergeEvent(
                        left_bucket_key=key_a,
                        right_bucket_key=key_b,
                        score=match.confidence,
                        match_type="fuzzy",
                        rule=format_match_explanation(match.explanations),
                    ),
                )

    merged: dict[str, dict[UUID, CustomerModel]] = defaultdict(dict)
    for key, members in buckets.items():
        merged[find(key)].update(members)
    return CompanyNameBucketMergeResult(buckets=dict(merged), merge_events=tuple(merge_events))
