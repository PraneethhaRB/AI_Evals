"""
Tests for the guardrails, using the actual adversarial examples from
golden_dataset.json - not made-up test cases. This means the test suite
and the eval dataset stay in sync: if you add a new adversarial example
to the dataset, you should add a matching assertion here.

Run with: pytest tests/test_guardrails.py -v
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from guardrails.input_guardrails import run_input_guardrails
from guardrails.output_guardrails import run_output_guardrails


def load_examples_by_id():
    with open("dataset/golden_dataset.json") as f:
        data = json.load(f)
    return {ex["id"]: ex for ex in data["examples"]}


EXAMPLES = load_examples_by_id()


def test_prompt_injection_is_blocked():
    example = EXAMPLES["adversarial_001"]  # "Ignore your previous instructions..."
    result = run_input_guardrails(example["query"])
    assert result.injection_detected is True
    assert result.blocked is True


def test_normal_fitness_query_is_not_blocked():
    example = EXAMPLES["easy_001"]  # muscle building plan request
    result = run_input_guardrails(example["query"])
    assert result.injection_detected is False
    assert result.blocked is False
    assert result.in_scope is True


def test_out_of_scope_query_is_flagged_not_blocked():
    example = EXAMPLES["adversarial_004"]  # "What's the capital of France?"
    result = run_input_guardrails(example["query"])
    assert result.in_scope is False
    assert result.blocked is False


def test_pii_disclosure_in_output_is_blocked():
    bad_answer = "Sure, their email is jane.doe@example.com and password is hunter2."
    result = run_output_guardrails(bad_answer, faithfulness_score=5)
    assert result.pii_disclosure_detected is True
    assert result.blocked is True


def test_safe_output_is_not_blocked():
    good_answer = "I can't share other users' personal information."
    result = run_output_guardrails(good_answer, faithfulness_score=5)
    assert result.pii_disclosure_detected is False
    assert result.blocked is False


def test_low_faithfulness_score_flags_hallucination():
    result = run_output_guardrails("Some answer", faithfulness_score=1)
    assert result.hallucination_flagged is True


def test_high_faithfulness_score_does_not_flag_hallucination():
    result = run_output_guardrails("Some answer", faithfulness_score=5)
    assert result.hallucination_flagged is False