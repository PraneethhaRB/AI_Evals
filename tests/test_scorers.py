"""
Tests for the statistical scorer - deterministic, no LLM calls, no network.
These run instantly and should always pass regardless of API keys or
running services, unlike the guardrail tests which touch real dataset
content but still avoid the network too.

Run with: pytest tests/test_scorers.py -v
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scorers.statistical_scorer import check_keywords, rouge_overlap, score_statistical


def test_keyword_check_passes_when_required_present_and_forbidden_absent():
    passed, missing, forbidden = check_keywords(
        answer="You should train 2-3 days per week with recovery in between.",
        must_contain=["2-3", "recovery"],
        must_not_contain=["daily"],
    )
    assert passed is True
    assert missing == []
    assert forbidden == []


def test_keyword_check_fails_when_required_keyword_missing():
    passed, missing, forbidden = check_keywords(
        answer="Train as often as you like.",
        must_contain=["2-3", "recovery"],
        must_not_contain=[],
    )
    assert passed is False
    assert "2-3" in missing
    assert "recovery" in missing


def test_keyword_check_fails_when_forbidden_keyword_present():
    passed, missing, forbidden = check_keywords(
        answer="Train daily for best results.",
        must_contain=[],
        must_not_contain=["daily"],
    )
    assert passed is False
    assert "daily" in forbidden


def test_keyword_check_is_case_insensitive():
    passed, missing, forbidden = check_keywords(
        answer="Make sure to include PROTEIN in your meal.",
        must_contain=["protein"],
        must_not_contain=[],
    )
    assert passed is True
    assert missing == []


def test_rouge_overlap_is_high_for_near_identical_text():
    score = rouge_overlap(
        answer="Beginners should train 2-3 days a week for recovery.",
        expected_answer="Beginners should strength train 2-3 non-consecutive days per week to allow adequate recovery.",
    )
    assert score > 0.4  # meaningful overlap, not an exact-match threshold


def test_rouge_overlap_is_low_for_unrelated_text():
    score = rouge_overlap(
        answer="The capital of France is Paris.",
        expected_answer="Beginners should strength train 2-3 non-consecutive days per week to allow adequate recovery.",
    )
    assert score < 0.15


def test_score_statistical_combines_keyword_and_rouge_checks():
    example = {
        "must_contain": ["protein"],
        "must_not_contain": ["supplement required"],
        "expected_answer": "Include a source of protein in your post-workout meal.",
    }
    result = score_statistical(
        answer="Eat a source of protein after your workout.",
        example=example,
    )
    assert result.keyword_check_passed is True
    assert result.missing_required_keywords == []
    assert result.forbidden_keywords_found == []
    assert 0.0 <= result.rouge_l_f1 <= 1.0


def test_score_statistical_flags_missing_keyword_even_with_good_rouge():
    # A paraphrase can score well on ROUGE while still missing a keyword
    # the golden dataset explicitly requires - this test protects the
    # keyword check from being silently trusted less than ROUGE.
    example = {
        "must_contain": ["BCrypt"],
        "must_not_contain": [],
        "expected_answer": "Passwords are hashed with BCrypt before storage.",
    }
    result = score_statistical(
        answer="Passwords are hashed securely before storage.",
        example=example,
    )
    assert result.keyword_check_passed is False
    assert "BCrypt" in result.missing_required_keywords