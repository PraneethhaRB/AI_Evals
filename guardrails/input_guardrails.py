"""
Input guardrails: run BEFORE a query reaches the subject system.

Why input-side matters separately from output-side: catching a prompt
injection attempt before generation means you never spend a generation
call on it, and you can respond with a fixed safe message instead of
hoping the model itself refuses correctly every time. Relying only on the
model to "just refuse" is not a guardrail - it's a hope.
"""

import re
from dataclasses import dataclass
import config


@dataclass
class InputGuardrailResult:
    injection_detected: bool
    injection_matched_pattern: str | None
    in_scope: bool
    blocked: bool  # True if the query should be blocked before generation


def detect_injection_fast(query: str) -> tuple:
    """
    Pattern-based check - instant, catches obvious/known injection phrasing.
    Returns (detected, matched_pattern_or_None).
    """
    query_lower = query.lower()
    for pattern in config.INJECTION_PATTERNS:
        if pattern in query_lower:
            return True, pattern
    return False, None


def check_in_scope(query: str) -> bool:
    """
    Coarse allowlist check: does the query relate to fitness/FitConnect at
    all? This is deliberately permissive (broad keyword list) since a false
    "out of scope" block is more annoying to a real user than an occasional
    off-topic question slipping through to get a polite redirect from the
    model itself.
    """
    query_lower = query.lower()
    return any(kw in query_lower for kw in config.IN_SCOPE_KEYWORDS)


def run_input_guardrails(query: str) -> InputGuardrailResult:
    injection_detected, matched_pattern = detect_injection_fast(query)
    in_scope = check_in_scope(query)

    # Only injection attempts hard-block before generation. Off-topic
    # queries are flagged (in_scope=False) but NOT blocked - the subject
    # system should still get a chance to respond with a polite redirect,
    # since blocking every off-topic message outright is a worse user
    # experience than letting the model say "that's outside what I help with."
    blocked = injection_detected

    return InputGuardrailResult(
        injection_detected=injection_detected,
        injection_matched_pattern=matched_pattern,
        in_scope=in_scope,
        blocked=blocked,
    )