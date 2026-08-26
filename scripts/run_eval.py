"""
Run this to evaluate every example in the golden dataset and print a
summary report.

Usage:
    python scripts/run_eval.py

Answers now come from your real subject systems via integrations/adapter_router.py,
which dispatches each example to the right adapter (rag_adapter,
coach_agent_adapter, multiagent_adapter) based on its target_system field.
"""

import json
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scorers.pipeline import evaluate_example
from guardrails.guardrail_engine import run_guardrails_pre_generation, run_guardrails_post_generation
from integrations.adapter_router import route_to_adapter


def load_dataset(path="dataset/golden_dataset.json") -> dict:
    with open(path, "r") as f:
        return json.load(f)


def run():
    dataset = load_dataset()
    examples = dataset["examples"]

    reports = []
    print(f"Running evaluation on {len(examples)} examples...\n")

    for example in examples:
        # Guardrails run FIRST on the query, before generation - matches
        # how this would work in a real deployment.
        should_proceed, input_guardrail_result = run_guardrails_pre_generation(example["query"])

        if not should_proceed:
            print(f"[BLOCKED-PRE] {example['id']} - injection pattern matched: "
                  f"'{input_guardrail_result.injection_matched_pattern}'")
            reports.append({
                "example_id": example["id"],
                "blocked_pre_generation": True,
                "reason": input_guardrail_result.injection_matched_pattern,
            })
            continue

        context_used, answer = route_to_adapter(example)

        # If the adapter couldn't reach the real service, don't waste an
        # LLM judge call scoring an error string - log it and move on.
        if answer.startswith("[ADAPTER_ERROR"):
            print(f"[ADAPTER_ERROR] {example['id']} ({example['target_system']}) - {answer}")
            reports.append({
                "example_id": example["id"],
                "target_system": example["target_system"],
                "adapter_error": answer,
            })
            continue

        report = evaluate_example(example, context_used, answer)

        # Output guardrails run after generation, reusing the faithfulness
        # score already computed above - no extra LLM call needed.
        output_guardrail_result = run_guardrails_post_generation(answer, report.faithfulness_score)

        reports.append(report)
        time.sleep(2)  # avoid bursting Groq's shared TPM limit across judge + multiagent calls
        status = "PASS" if (report.faithfulness_passed and report.relevance_passed) else "FAIL"
        guardrail_flag = " [GUARDRAIL-BLOCKED]" if output_guardrail_result.blocked else ""
        print(f"[{status}]{guardrail_flag} {report.example_id} ({report.target_system}) "
              f"- faithfulness={report.faithfulness_score} relevance={report.relevance_score}")

    total = len(reports)
    passed = sum(
        1 for r in reports
        if hasattr(r, "faithfulness_passed") and r.faithfulness_passed and r.relevance_passed
    )
    blocked_pre = sum(1 for r in reports if isinstance(r, dict) and r.get("blocked_pre_generation"))
    adapter_errors = sum(1 for r in reports if isinstance(r, dict) and r.get("adapter_error"))
    print(f"\nSummary: {passed}/{total} passed both thresholds, "
          f"{blocked_pre} blocked pre-generation, {adapter_errors} adapter errors.")

    # Save full detail for the dashboard (Phase 5) to consume later.
    # Dict entries (blocked/error) are already serializable; scored
    # reports are dataclasses and need __dict__.
    serializable = [r if isinstance(r, dict) else r.__dict__ for r in reports]
    os.makedirs("results", exist_ok=True)
    with open("results/latest_run.json", "w") as f:
        json.dump(serializable, f, indent=2)
    print("Full report written to results/latest_run.json")


if __name__ == "__main__":
    run()