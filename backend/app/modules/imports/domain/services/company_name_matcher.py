"""Token-based company name matching with confidence bands."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from app.modules.imports.domain.services.company_name_normalizer import (
    SECTOR_GENERIC_TOKENS,
    canonical_token_set,
    canonicalize_token,
    core_tokens,
    normalize_import_company_name,
    tokenize_company_name,
)

MATCH_SCORE_MIN = 70
MATCH_SCORE_STRONG = 95
MATCH_SCORE_POSSIBLE = 85

EXPLANATION_NORMALIZED_EXACT = "normalized_exact"
EXPLANATION_TOKEN_OVERLAP_HIGH = "token_overlap_high"
EXPLANATION_LEGAL_SUFFIX_IGNORED = "legal_suffix_ignored"
EXPLANATION_ABBREVIATION_NORMALIZED = "abbreviation_normalized"
EXPLANATION_STRING_SIMILARITY = "string_similarity_high"


@dataclass(frozen=True)
class CompanyNameMatchScore:
    confidence: int
    explanations: tuple[str, ...]


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _overlap_ratio(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def _first_token_blocks_match(core_a: list[str], core_b: list[str]) -> bool:
    """Reject matches where brand/first token clearly differs (false positive guard)."""
    if not core_a or not core_b:
        return False
    if core_a[0] == core_b[0]:
        return False
    similarity = SequenceMatcher(None, core_a[0], core_b[0]).ratio()
    if core_a[0].startswith(core_b[0]) or core_b[0].startswith(core_a[0]):
        # Prefix siblings (e.g. agro vs agrowell) are different brands unless nearly identical.
        return similarity < 0.92
    return similarity < 0.82


def _sector_only_overlap(set_a: set[str], set_b: set[str]) -> bool:
    """True when overlap is only generic sector words and brand tokens differ on both sides."""
    shared = set_a & set_b
    if not shared or not shared.issubset(SECTOR_GENERIC_TOKENS):
        return False
    distinctive_a = set_a - SECTOR_GENERIC_TOKENS
    distinctive_b = set_b - SECTOR_GENERIC_TOKENS
    if not distinctive_a or not distinctive_b:
        return False
    return not (distinctive_a & distinctive_b)


def _distinctive_tail_mismatch(core_a: list[str], core_b: list[str]) -> bool:
    """Same leading token but differing distinctive tail tokens (e.g. ANADOLU GIDA vs ANADOLU MAKINA)."""
    if len(core_a) < 2 or len(core_b) < 2:
        return False
    if core_a[0] != core_b[0]:
        return False
    tail_a = set(core_a[1:])
    tail_b = set(core_b[1:])
    return bool(tail_a and tail_b and not (tail_a & tail_b))


def score_company_name_pair(query: str, candidate: str) -> CompanyNameMatchScore | None:
    """Score import company name against CRM customer name. Returns None if below MIN threshold."""
    norm_q = normalize_import_company_name(query)
    norm_c = normalize_import_company_name(candidate)
    if not norm_q or not norm_c:
        return None

    explanations: list[str] = []

    if norm_q == norm_c:
        return CompanyNameMatchScore(confidence=100, explanations=(EXPLANATION_NORMALIZED_EXACT,))

    tokens_q = tokenize_company_name(norm_q)
    tokens_c = tokenize_company_name(norm_c)
    core_q = core_tokens(tokens_q)
    core_c = core_tokens(tokens_c)

    if _first_token_blocks_match(core_q, core_c):
        return None

    if _distinctive_tail_mismatch(core_q, core_c):
        return None

    set_q = canonical_token_set(core_q)
    set_c = canonical_token_set(core_c)

    if _sector_only_overlap(set_q, set_c):
        return None

    jaccard = _jaccard(set_q, set_c)
    overlap = _overlap_ratio(set_q, set_c)
    seq_core = SequenceMatcher(None, " ".join(core_q), " ".join(core_c)).ratio()
    seq_full = SequenceMatcher(None, norm_q, norm_c).ratio()

    if jaccard >= 0.75 or overlap >= 0.85:
        explanations.append(EXPLANATION_TOKEN_OVERLAP_HIGH)

    full_q = canonical_token_set(tokens_q)
    full_c = canonical_token_set(tokens_c)
    if full_q != full_c and set_q == set_c:
        explanations.append(EXPLANATION_LEGAL_SUFFIX_IGNORED)

    if tokens_q != core_q or tokens_c != core_c:
        if any(canonicalize_token(t) != t for t in tokens_q + tokens_c):
            explanations.append(EXPLANATION_ABBREVIATION_NORMALIZED)

    if seq_core >= 0.88 or seq_full >= 0.9:
        explanations.append(EXPLANATION_STRING_SIMILARITY)

    score = max(jaccard * 100, overlap * 98, seq_core * 100, seq_full * 95)

    # Subset boost: shorter distinctive name fully contained in longer
    if set_q and set_c and (set_q <= set_c or set_c <= set_q):
        score = max(score, 93.0)

    confidence = int(round(min(score, 100)))
    if confidence < MATCH_SCORE_MIN:
        return None

    return CompanyNameMatchScore(
        confidence=confidence,
        explanations=tuple(dict.fromkeys(explanations)),
    )


def format_match_explanation(explanations: tuple[str, ...]) -> str:
    return ", ".join(explanations)
