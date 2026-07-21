"""Company-name fuzzy duplicate grouping — used only by Duplicate Customer Analysis."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from uuid import UUID

from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.imports.domain.services.company_name_matcher import (
    MATCH_SCORE_MIN,
    format_match_explanation,
    is_short_single_token_hub,
    score_company_name_pair,
)
from app.modules.imports.domain.services.company_name_normalizer import (
    core_tokens,
    normalize_import_company_name,
    tokenize_company_name,
)

# Below this size, evaluate all pairs in a first-token block (legacy behaviour).
# Above this size, do NOT skip the block — generate candidates via secondary indexes
# (second/third core token + remainder prefix), similar to Import CustomerMatchIndex.
_COMPANY_NAME_SIMILARITY_DIRECT_PAIRWISE_MAX = 32


@dataclass(frozen=True)
class CompanyNameBucketMergeEvent:
    left_bucket_key: str
    right_bucket_key: str
    score: int
    match_type: str
    rule: str


@dataclass(frozen=True)
class CompanyNameMergeStats:
    """Diagnostics for large-bucket candidate narrowing (read-only reporting)."""

    first_token_blocks: int
    blocks_above_direct_pairwise: int
    theoretical_naive_pairs: int
    candidate_pairs_generated: int
    pairs_scored: int
    pairs_accepted: int


@dataclass(frozen=True)
class CompanyNameBucketMergeResult:
    buckets: dict[str, dict[UUID, CustomerModel]]
    merge_events: tuple[CompanyNameBucketMergeEvent, ...]
    stats: CompanyNameMergeStats | None = None


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


def _core_tokens_for_name(name: str) -> list[str]:
    normalized = normalize_import_company_name(name)
    return core_tokens(tokenize_company_name(normalized))


def is_short_hub_bucket_key(bucket_key: str) -> bool:
    """Bucket keyed by a single short token (e.g. ABC, SDK) — fuzzy merge hub candidate."""
    tokens = _normalized_bucket_tokens(bucket_key)
    return is_short_single_token_hub(core_tokens(tokens))


def is_bare_brand_hub_bucket_key(bucket_key: str) -> bool:
    """Single core-token bucket of any length (ACARLAR, IDEAL, AKTIF, ABC, …).

    These must not participate in Admin fuzzy union-find: a bare brand matching two
    unrelated multi-token names would otherwise transitively merge them.
    """
    tokens = _normalized_bucket_tokens(bucket_key)
    return len(core_tokens(tokens)) == 1


def is_bare_brand_hub_name(name: str) -> bool:
    """True when the display/legal name collapses to a single core token."""
    return len(_core_tokens_for_name(name)) == 1


def _customer_company_name_for_grouping(model: CustomerModel) -> str:
    if model.legal_name and model.legal_name.strip():
        return model.legal_name.strip()
    return model.display_name.strip()


def _bucket_is_fuzzy_merge_eligible(bucket_key: str) -> bool:
    # Includes SHORT_HUB (≤4) and longer bare brands (ACARLAR, IDEAL, …).
    return not is_bare_brand_hub_bucket_key(bucket_key)


def _narrowing_keys_for_bucket(bucket_key: str) -> frozenset[str]:
    """Secondary blocking keys within a first-token block (Import-like narrowing).

    - ``t2:`` second core token
    - ``t23:`` second+third core tokens (tighter)
    - ``rp:`` prefix of normalized remainder after the first whitespace token
    """
    display = bucket_key.replace("_", " ")
    cores = _core_tokens_for_name(display)
    keys: set[str] = set()
    if len(cores) >= 2:
        keys.add(f"t2:{cores[1]}")
    if len(cores) >= 3:
        keys.add(f"t23:{cores[1]}|{cores[2]}")

    normalized = normalize_import_company_name(display) or display.lower()
    parts = normalized.split()
    if len(parts) >= 2:
        remainder = " ".join(parts[1:])
        prefix_len = min(3, len(remainder))
        if prefix_len:
            keys.add(f"rp:{remainder[:prefix_len]}")

    return frozenset(keys) if keys else frozenset({"__orphan__"})


def _pair_sort_key(left: str, right: str) -> tuple[str, str]:
    return (left, right) if left <= right else (right, left)


def _candidate_pairs_for_block(block: list[str]) -> list[tuple[str, str]]:
    """Generate candidate bucket-key pairs inside one first-token block.

    Small blocks: full pairwise (same as pre-Problem-C behaviour without skip).
    Large blocks: pairs that share a secondary narrowing key. Coarse ``t2:`` indexes
    that themselves exceed the direct-pairwise cap are skipped so sector-generic
    second tokens (e.g. electrical) do not re-introduce near-N×N work; tighter
    ``t23:`` / ``rp:`` indexes still cover strong duplicates.
    """
    if len(block) < 2:
        return []

    if len(block) <= _COMPANY_NAME_SIMILARITY_DIRECT_PAIRWISE_MAX:
        return [
            (block[index], other)
            for index in range(len(block))
            for other in block[index + 1 :]
        ]

    index: dict[str, list[str]] = defaultdict(list)
    for key in block:
        for narrowing_key in _narrowing_keys_for_bucket(key):
            index[narrowing_key].append(key)

    pairs: set[tuple[str, str]] = set()
    for narrowing_key, members in index.items():
        unique_members = sorted(set(members))
        if len(unique_members) < 2:
            continue
        # Soft cap on every secondary index (t2 / t23 / rp): oversized coarse keys
        # (e.g. rp:uni for UNIQUE000…UNIQUE099) must not re-introduce near-N×N work.
        if len(unique_members) > _COMPANY_NAME_SIMILARITY_DIRECT_PAIRWISE_MAX:
            continue
        for index_a, key_a in enumerate(unique_members):
            for key_b in unique_members[index_a + 1 :]:
                pairs.add(_pair_sort_key(key_a, key_b))
    return sorted(pairs)


def _length_prefilter_ok(name_a: str, name_b: str) -> bool:
    """Mirror Import CustomerMatchIndex length gate (normalized string lengths)."""
    norm_a = normalize_import_company_name(name_a) or name_a
    norm_b = normalize_import_company_name(name_b) or name_b
    len_a = len(norm_a)
    len_b = len(norm_b)
    return abs(len_a - len_b) <= max(12, int(max(len_a, len_b) * 0.75))


def merge_similar_company_name_buckets(
    buckets: dict[str, dict[UUID, CustomerModel]],
) -> CompanyNameBucketMergeResult:
    """Union exact-normalized buckets whose names score as duplicates (Import matcher).

    Uses ``score_company_name_pair`` with the same ``MATCH_SCORE_MIN`` floor as
    Import ``CustomerMatchIndex``. Admin-only guard: bare single-token brand hubs
    are excluded from fuzzy edges so they cannot transitively bridge unrelated
    multi-token companies (e.g. ACARLAR linking VAGON and YAPI).

    Large first-token blocks (>32) are no longer skipped: candidates are narrowed
    via second/third core-token and remainder-prefix indexes before scoring.
    """
    if len(buckets) < 2:
        empty_stats = CompanyNameMergeStats(
            first_token_blocks=0,
            blocks_above_direct_pairwise=0,
            theoretical_naive_pairs=0,
            candidate_pairs_generated=0,
            pairs_scored=0,
            pairs_accepted=0,
        )
        return CompanyNameBucketMergeResult(buckets=buckets, merge_events=(), stats=empty_stats)

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

    theoretical_naive_pairs = 0
    candidate_pairs_generated = 0
    pairs_scored = 0
    pairs_accepted = 0
    blocks_above_direct = 0

    for block in block_keys.values():
        if len(block) < 2:
            continue
        n = len(block)
        theoretical_naive_pairs += n * (n - 1) // 2
        if n > _COMPANY_NAME_SIMILARITY_DIRECT_PAIRWISE_MAX:
            blocks_above_direct += 1

        candidate_pairs = _candidate_pairs_for_block(block)
        candidate_pairs_generated += len(candidate_pairs)

        for key_a, key_b in candidate_pairs:
            if find(key_a) == find(key_b):
                continue
            if not _bucket_is_fuzzy_merge_eligible(key_a) or len(buckets[key_a]) == 0:
                continue
            if not _bucket_is_fuzzy_merge_eligible(key_b) or len(buckets[key_b]) == 0:
                continue
            representative_a = next(iter(buckets[key_a].values()))
            name_a = _customer_company_name_for_grouping(representative_a)
            if is_bare_brand_hub_name(name_a):
                continue
            representative_b = next(iter(buckets[key_b].values()))
            name_b = _customer_company_name_for_grouping(representative_b)
            if is_bare_brand_hub_name(name_b):
                continue
            if not _length_prefilter_ok(name_a, name_b):
                continue
            pairs_scored += 1
            match = score_company_name_pair(name_a, name_b)
            # Same acceptance floor as Import CustomerMatchIndex (MATCH_SCORE_MIN).
            if match is None or match.confidence < MATCH_SCORE_MIN:
                continue
            pairs_accepted += 1
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

    stats = CompanyNameMergeStats(
        first_token_blocks=len(block_keys),
        blocks_above_direct_pairwise=blocks_above_direct,
        theoretical_naive_pairs=theoretical_naive_pairs,
        candidate_pairs_generated=candidate_pairs_generated,
        pairs_scored=pairs_scored,
        pairs_accepted=pairs_accepted,
    )
    return CompanyNameBucketMergeResult(
        buckets=dict(merged),
        merge_events=tuple(merge_events),
        stats=stats,
    )
