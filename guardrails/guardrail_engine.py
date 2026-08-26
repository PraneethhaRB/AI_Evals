"""
Guardrail engine: combines input + output guardrails into one call.
Mirrors scorers/pipeline.py's role - this is the single entry point the
API (Phase 4) will call, so it never has to know about individual
guardrail modules directly.
"""

from dataclasses import dataclass, asdict
from guardrails.input_guardrails import run_input_guardrails
from guardrails.output_guardrails import run_output_guardrails


@dataclass
class GuardrailReport:
    input_result: dict
    output_result: dict | None  # None if input was blocked, since generation never happened
    final_blocked: bool
    block_reason: str | None


def run_guardrails_pre_generation(query: str) -> tuple:
    """
    Call this BEFORE running the query through your subject system.
    Returns (should_proceed, input_result).
    If should_proceed is False, skip generation entirely and show a safe
    fixed response instead - don't spend a generation call on it.
    """
    input_result = run_input_guardrails(query)
    should_proceed = not input_result.blocked
    return should_proceed, input_result


def run_guardrails_post_generation(answer: str, faithfulness_score: int):
    """
    Call this AFTER generation, using the faithfulness score already
    produced by scorers/pipeline.py's evaluate_example().
    """
    return run_output_guardrails(answer, faithfulness_score)


def full_guardrail_report(query: str, answer: str | None, faithfulness_score: int | None) -> GuardrailReport:
    """
    Convenience wrapper for logging/dashboard purposes: runs both stages
    and returns one combined report. `answer` and `faithfulness_score` can
    be None if the input was already blocked before generation happened.
    """
    should_proceed, input_result = run_guardrails_pre_generation(query)

    if not should_proceed:
        return GuardrailReport(
            input_result=asdict(input_result),
            output_result=None,
            final_blocked=True,
            block_reason=f"input_injection:{input_result.injection_matched_pattern}",
        )

    output_result = run_guardrails_post_generation(answer, faithfulness_score)
    block_reason = None
    if output_result.blocked:
        if output_result.pii_disclosure_detected:
            block_reason = "output_pii_disclosure"
        elif output_result.unsafe_content_detected:
            block_reason = "output_unsafe_content"

    return GuardrailReport(
        input_result=asdict(input_result),
        output_result=asdict(output_result),
        final_blocked=output_result.blocked,
        block_reason=block_reason,
    )