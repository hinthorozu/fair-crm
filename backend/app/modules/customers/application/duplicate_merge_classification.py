"""Duplicate merge match classification, review tiers, and human-readable explanations."""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.imports.domain.services.company_name_matcher import (
    EXPLANATION_ABBREVIATION_NORMALIZED,
    EXPLANATION_DISTINCTIVE_OVERLAP_REQUIRED,
    EXPLANATION_LEGAL_SUFFIX_IGNORED,
    EXPLANATION_NORMALIZED_EXACT,
    EXPLANATION_SHORT_HUB_BLOCKED,
    EXPLANATION_STRING_SIMILARITY,
    EXPLANATION_TOKEN_OVERLAP_HIGH,
    MATCH_SCORE_MIN,
    MATCH_SCORE_POSSIBLE,
    MATCH_SCORE_STRONG,
)

MERGE_CLASS_STRONG = "strong_duplicate"
MERGE_CLASS_PROBABLE = "probable_duplicate"
MERGE_CLASS_POSSIBLE = "possible_duplicate"
MERGE_CLASS_MANUAL = "manual_review"

REVIEW_TIER_READY = "ready"
REVIEW_TIER_NEEDS_REVIEW = "needs_review"

EXACT_REASON_CODES = frozenset(
    {
        "normalized_exact",
        "exact_normalized",
        "exact_company_name",
        "exact_email",
        "exact_website",
        "exact_phone",
        "email_exact_match",
        "phone_exact_match",
    }
)

EXPLANATION_LABELS: dict[str, str] = {
    EXPLANATION_NORMALIZED_EXACT: "Exact normalized company name match",
    EXPLANATION_TOKEN_OVERLAP_HIGH: "High token overlap after normalization",
    EXPLANATION_LEGAL_SUFFIX_IGNORED: "Legal suffix difference ignored",
    EXPLANATION_ABBREVIATION_NORMALIZED: "Abbreviation normalized to canonical form",
    EXPLANATION_STRING_SIMILARITY: "High string similarity after normalization",
    EXPLANATION_SHORT_HUB_BLOCKED: "Short single-token hub match blocked",
    EXPLANATION_DISTINCTIVE_OVERLAP_REQUIRED: "Insufficient distinctive token overlap",
    "exact_normalized": "Exact normalized company name match",
    "exact_company_name": "Exact normalized company name match",
    "exact_email": "Exact email address match",
    "exact_website": "Exact website match",
    "exact_phone": "Exact phone number match",
    "email_exact_match": "Exact email address match",
    "phone_exact_match": "Exact phone number match",
    "group_anchor": "Reference customer in duplicate group",
    "transitive_group_member": "Grouped via another duplicate link in the cluster",
}


@dataclass(frozen=True)
class GroupMatchSummary:
    min_match_score: int | None
    max_match_score: int | None
    merge_classification: str
    review_tier: str
    requires_manual_review: bool
    match_explanation_summary: str


def classify_duplicate_match(
    *,
    match_score: int | None,
    duplicate_reason: str | None,
) -> str:
    if duplicate_reason in EXACT_REASON_CODES or (
        duplicate_reason is not None and duplicate_reason.startswith("exact_")
    ):
        return MERGE_CLASS_STRONG
    if match_score is None:
        return MERGE_CLASS_MANUAL
    if match_score >= MATCH_SCORE_STRONG:
        return MERGE_CLASS_STRONG
    if match_score >= MATCH_SCORE_POSSIBLE:
        return MERGE_CLASS_PROBABLE
    if match_score >= MATCH_SCORE_MIN:
        return MERGE_CLASS_POSSIBLE
    return MERGE_CLASS_MANUAL


def review_tier_for_classification(merge_classification: str) -> str:
    if merge_classification == MERGE_CLASS_STRONG:
        return REVIEW_TIER_READY
    return REVIEW_TIER_NEEDS_REVIEW


def requires_manual_review(merge_classification: str) -> bool:
    return merge_classification != MERGE_CLASS_STRONG


def humanize_duplicate_reason(duplicate_reason: str | None) -> str | None:
    if not duplicate_reason:
        return None
    if duplicate_reason in EXPLANATION_LABELS:
        return EXPLANATION_LABELS[duplicate_reason]
    if duplicate_reason.startswith("exact_normalized:"):
        bucket = duplicate_reason.split(":", 1)[1]
        return f"Exact normalized match (bucket {bucket})"
    if duplicate_reason.startswith("fuzzy:"):
        pair = duplicate_reason.removeprefix("fuzzy:")
        return f"Fuzzy company name match merged buckets ({pair})"
    if "," in duplicate_reason:
        parts = [humanize_duplicate_reason(part.strip()) or part.strip() for part in duplicate_reason.split(",")]
        return "; ".join(parts)
    return duplicate_reason.replace("_", " ")


def summarize_group_match(
    *,
    match_scores: list[int | None],
    duplicate_reasons: list[str | None],
) -> GroupMatchSummary:
    scores = [score for score in match_scores if score is not None]
    min_score = min(scores) if scores else None
    max_score = max(scores) if scores else None

    classifications = [
        classify_duplicate_match(match_score=score, duplicate_reason=reason)
        for score, reason in zip(match_scores, duplicate_reasons, strict=False)
    ]
    if MERGE_CLASS_MANUAL in classifications:
        merge_classification = MERGE_CLASS_MANUAL
    elif MERGE_CLASS_POSSIBLE in classifications:
        merge_classification = MERGE_CLASS_POSSIBLE
    elif MERGE_CLASS_PROBABLE in classifications:
        merge_classification = MERGE_CLASS_PROBABLE
    else:
        merge_classification = MERGE_CLASS_STRONG

    review_tier = review_tier_for_classification(merge_classification)
    explanation_parts: list[str] = []
    for reason in duplicate_reasons:
        label = humanize_duplicate_reason(reason)
        if label and label not in explanation_parts:
            explanation_parts.append(label)
    if min_score is not None and max_score is not None:
        if min_score == max_score:
            explanation_parts.insert(0, f"Match score {min_score}")
        else:
            explanation_parts.insert(0, f"Match scores {min_score}-{max_score}")

    return GroupMatchSummary(
        min_match_score=min_score,
        max_match_score=max_score,
        merge_classification=merge_classification,
        review_tier=review_tier,
        requires_manual_review=requires_manual_review(merge_classification),
        match_explanation_summary=" · ".join(explanation_parts) if explanation_parts else "Duplicate group",
    )


def manual_review_warning_message(summary: GroupMatchSummary) -> str | None:
    if not summary.requires_manual_review:
        return None
    if summary.merge_classification == MERGE_CLASS_POSSIBLE:
        return (
            "Manual review required — possible duplicate match (lower confidence). "
            "Verify company identity before merging."
        )
    if summary.merge_classification == MERGE_CLASS_PROBABLE:
        return (
            "Manual review recommended — probable duplicate match. "
            "Confirm the companies are the same legal entity before merging."
        )
    return (
        "Manual review required — duplicate link confidence could not be scored automatically. "
        "Inspect all customers in this group before merging."
    )
