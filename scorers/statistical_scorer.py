"""
Statistical scorers: fast, deterministic, no LLM call.

Why these run first: they're free and instant, so they catch obvious
failures (a required keyword missing, a forbidden phrase present) before
you spend Groq API calls/tokens on the LLM judge. Think of this as a
cheap pre-filter, not a replacement for the judge - it can't tell you if
an answer is *actually* correct, only whether it matches surface-level
expectations from the golden dataset.
"""

from dataclasses import dataclass
from rouge_score import rouge_scorer
import config


@dataclass
class StatisticalResult:
    keyword_check_passed: bool
    missing_required_keywords: list
    forbidden_keywords_found: list
    rouge_l_f1: float  # overlap with expected_answer, 0.0-1.0


def check_keywords(answer: str, must_contain: list, must_not_contain: list) -> tuple:
    """
    Returns (passed, missing_required, forbidden_found).
    Case-insensitive substring match - simple on purpose, since this is a
    pre-filter, not the final word on quality.
    """
    answer_lower = answer.lower()

    missing_required = [
        kw for kw in must_contain if kw.lower() not in answer_lower
    ]
    forbidden_found = [
        kw for kw in must_not_contain if kw.lower() in answer_lower
    ]

    passed = len(missing_required) == 0 and len(forbidden_found) == 0
    return passed, missing_required, forbidden_found


def rouge_overlap(answer: str, expected_answer: str) -> float:
    """
    ROUGE-L F1 score between the generated answer and the golden dataset's
    expected_answer. This is NOT a pass/fail signal by itself - two correct
    answers can be phrased very differently and score low here. It's a
    supporting signal, most useful for flagging answers that are
    suspiciously far from what was expected (worth a human look).
    """
    scorer = rouge_scorer.RougeScorer([config.ROUGE_TYPE], use_stemmer=True)
    scores = scorer.score(expected_answer, answer)
    return scores[config.ROUGE_TYPE].fmeasure


def score_statistical(answer: str, example: dict) -> StatisticalResult:
    """
    Runs all statistical checks for a single golden dataset example.
    `example` is one entry from golden_dataset.json's "examples" list.
    """
    passed, missing, forbidden = check_keywords(
        answer,
        example.get("must_contain", []),
        example.get("must_not_contain", []),
    )
    rouge_f1 = rouge_overlap(answer, example.get("expected_answer", ""))

    return StatisticalResult(
        keyword_check_passed=passed,
        missing_required_keywords=missing,
        forbidden_keywords_found=forbidden,
        rouge_l_f1=round(rouge_f1, 3),
    )
