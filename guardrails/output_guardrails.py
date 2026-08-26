"""
Output guardrails: run AFTER generation, before the answer reaches the user.

Three checks:
1. Hallucination gate - reuses the faithfulness score you already computed
   in Phase 2, so this guardrail costs nothing extra to run.
2. PII disclosure - regex + phrase check for the answer leaking data it
   shouldn't (e.g. another user's email).
3. Unsafe content - coarse keyword pre-filter (see config.py note on why
   this needs a real moderation model in production, not just this list).
"""

import re
from dataclasses import dataclass
import config


@dataclass
class OutputGuardrailResult:
    hallucination_flagged: bool
    pii_disclosure_detected: bool
    pii_matches: list
    unsafe_content_detected: bool
    blocked: bool  # True if the answer should be blocked/replaced before showing the user


def check_hallucination_gate(faithfulness_score: int) -> bool:
    """
    Returns True if the answer should be flagged for hallucination, based
    on the faithfulness score already produced by scorers/llm_judge_scorer.py.
    This is a gate, not a re-score - it deliberately reuses Phase 2's output
    instead of asking the LLM the same question twice.
    """
    return faithfulness_score < config.FAITHFULNESS_PASS_THRESHOLD


def check_pii_disclosure(answer: str) -> tuple:
    """
    Returns (detected, list_of_matches). Combines regex pattern matches
    (email/phone) with phrase-based checks (e.g. "password is") since a
    regex alone won't catch "their password is hunter2" style disclosures
    that don't match a structured pattern.
    """
    matches = []

    for label, pattern in config.PII_REGEX_PATTERNS.items():
        found = re.findall(pattern, answer)
        if found:
            matches.append({"type": label, "matches": found})

    answer_lower = answer.lower()
    for phrase in config.PII_DISCLOSURE_PHRASES:
        if phrase in answer_lower:
            matches.append({"type": "disclosure_phrase", "matches": [phrase]})

    return len(matches) > 0, matches


def check_unsafe_content(answer: str) -> bool:
    answer_lower = answer.lower()
    return any(kw in answer_lower for kw in config.UNSAFE_CONTENT_KEYWORDS)


def run_output_guardrails(answer: str, faithfulness_score: int) -> OutputGuardrailResult:
    hallucination_flagged = check_hallucination_gate(faithfulness_score)
    pii_detected, pii_matches = check_pii_disclosure(answer)
    unsafe_detected = check_unsafe_content(answer)

    # PII disclosure and unsafe content are hard blocks - these should
    # never reach a user regardless of how good the answer otherwise is.
    # Hallucination is flagged but not auto-blocked here, since a low
    # faithfulness score can be a false positive from the judge - in a
    # real deployment you'd route flagged-but-not-blocked answers to a
    # human review queue rather than silently showing or hiding them.
    blocked = pii_detected or unsafe_detected

    return OutputGuardrailResult(
        hallucination_flagged=hallucination_flagged,
        pii_disclosure_detected=pii_detected,
        pii_matches=pii_matches,
        unsafe_content_detected=unsafe_detected,
        blocked=blocked,
    )