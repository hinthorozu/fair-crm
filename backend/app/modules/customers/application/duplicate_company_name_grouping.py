"""Company-name fuzzy duplicate grouping — used only by Duplicate Customer Analysis."""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from app.modules.customers.infrastructure.persistence.models import CustomerModel

_COMPANY_NAME_SIMILARITY_MAX_BLOCK = 32


def _company_name_block_key(normalized: str) -> str:
    tokens = [token for token in normalized.split() if len(token) > 2]
    if not tokens:
        tokens = [token for token in normalized.split() if token]
    return tokens[0] if tokens else normalized


def _customer_company_name_for_grouping(model: CustomerModel) -> str:
    if model.legal_name and model.legal_name.strip():
        return model.legal_name.strip()
    return model.display_name.strip()


def merge_similar_company_name_buckets(
    buckets: dict[str, dict[UUID, CustomerModel]],
) -> dict[str, dict[UUID, CustomerModel]]:
    """Union exact-normalized buckets whose display names score as probable duplicates."""
    if len(buckets) < 2:
        return buckets

    from app.modules.imports.domain.services.company_name_matcher import (
        MATCH_SCORE_POSSIBLE,
        score_company_name_pair,
    )

    keys = sorted(buckets.keys())
    canonical: dict[str, str] = {key: key for key in keys}

    def find(key: str) -> str:
        while canonical[key] != key:
            canonical[key] = canonical[canonical[key]]
            key = canonical[key]
        return key

    def union(left: str, right: str) -> None:
        root_left = find(left)
        root_right = find(right)
        if root_left == root_right:
            return
        if root_left <= root_right:
            canonical[root_right] = root_left
        else:
            canonical[root_left] = root_right

    block_keys: dict[str, list[str]] = defaultdict(list)
    for key in keys:
        block_keys[_company_name_block_key(key)].append(key)

    for block in block_keys.values():
        if len(block) < 2 or len(block) > _COMPANY_NAME_SIMILARITY_MAX_BLOCK:
            continue
        for index, key_a in enumerate(block):
            if len(buckets[key_a]) == 0:
                continue
            representative_a = next(iter(buckets[key_a].values()))
            name_a = _customer_company_name_for_grouping(representative_a)
            for key_b in block[index + 1 :]:
                if key_a == key_b or find(key_a) == find(key_b):
                    continue
                if len(buckets[key_b]) == 0:
                    continue
                representative_b = next(iter(buckets[key_b].values()))
                name_b = _customer_company_name_for_grouping(representative_b)
                match = score_company_name_pair(name_a, name_b)
                if match is not None and match.confidence >= MATCH_SCORE_POSSIBLE:
                    union(key_a, key_b)

    merged: dict[str, dict[UUID, CustomerModel]] = defaultdict(dict)
    for key, members in buckets.items():
        merged[find(key)].update(members)
    return dict(merged)
