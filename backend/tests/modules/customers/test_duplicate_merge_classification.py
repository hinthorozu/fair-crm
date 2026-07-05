"""Unit tests for duplicate merge classification and explanations."""

from app.modules.customers.application.duplicate_merge_classification import (
    MERGE_CLASS_MANUAL,
    MERGE_CLASS_POSSIBLE,
    MERGE_CLASS_PROBABLE,
    MERGE_CLASS_STRONG,
    REVIEW_TIER_NEEDS_REVIEW,
    REVIEW_TIER_READY,
    classify_duplicate_match,
    humanize_duplicate_reason,
    manual_review_warning_message,
    requires_manual_review,
    review_tier_for_classification,
    summarize_group_match,
)


def test_classify_exact_email_match_as_strong():
    assert classify_duplicate_match(match_score=None, duplicate_reason="exact_email") == MERGE_CLASS_STRONG
    assert review_tier_for_classification(MERGE_CLASS_STRONG) == REVIEW_TIER_READY
    assert requires_manual_review(MERGE_CLASS_STRONG) is False


def test_classify_fuzzy_scores_by_threshold():
    assert classify_duplicate_match(match_score=96, duplicate_reason="token_overlap_high") == MERGE_CLASS_STRONG
    assert classify_duplicate_match(match_score=90, duplicate_reason="token_overlap_high") == MERGE_CLASS_PROBABLE
    assert classify_duplicate_match(match_score=75, duplicate_reason="token_overlap_high") == MERGE_CLASS_POSSIBLE
    assert classify_duplicate_match(match_score=50, duplicate_reason="token_overlap_high") == MERGE_CLASS_MANUAL


def test_humanize_duplicate_reason_covers_known_codes():
    assert humanize_duplicate_reason("exact_email") == "Exact email address match"
    assert humanize_duplicate_reason("token_overlap_high") == "High token overlap after normalization"
    assert humanize_duplicate_reason("short_single_token_hub_blocked") == "Short single-token hub match blocked"


def test_summarize_group_match_uses_weakest_member_classification():
    summary = summarize_group_match(
        match_scores=[100, 78],
        duplicate_reasons=["exact_normalized", "token_overlap_high"],
    )
    assert summary.min_match_score == 78
    assert summary.max_match_score == 100
    assert summary.merge_classification == MERGE_CLASS_POSSIBLE
    assert summary.review_tier == REVIEW_TIER_NEEDS_REVIEW
    assert summary.requires_manual_review is True
    assert "78" in summary.match_explanation_summary


def test_manual_review_warning_message_for_probable_and_possible():
    probable = summarize_group_match(
        match_scores=[90],
        duplicate_reasons=["token_overlap_high"],
    )
    possible = summarize_group_match(
        match_scores=[75],
        duplicate_reasons=["token_overlap_high"],
    )
    strong = summarize_group_match(
        match_scores=[100],
        duplicate_reasons=["exact_normalized"],
    )

    assert manual_review_warning_message(strong) is None
    assert "probable duplicate" in (manual_review_warning_message(probable) or "").lower()
    assert "possible duplicate" in (manual_review_warning_message(possible) or "").lower()
