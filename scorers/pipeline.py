"""
Pipeline: combines statistical_scorer + llm_judge_scorer into one function
that produces a single report per example. This is the function the API
(Phase 4) and dashboard (Phase 5) will actually call - they should never
need to call individual scorers directly.
"""

from dataclasses import dataclass, asdict
import config
from scorers.statistical_scorer import score_statistical
from scorers.llm_judge_scorer import score_with_judge


@dataclass
class EvaluationReport:
    example_id: str
    target_system: str
    query: str
    answer: str
    statistical: dict
    faithfulness_score: int
    faithfulness_reasoning: str
    relevance_score: int
    relevance_reasoning: str
    faithfulness_passed: bool
    relevance_passed: bool


def evaluate_example(example: dict, context_used: str, answer: str) -> EvaluationReport:
    """
    example: one entry from golden_dataset.json's "examples" list
    context_used: the context the subject system actually used to generate
                   the answer (RAG chunks / Research Agent output / user
                   stats+messages for the Coach Agent)
    answer: the subject system's generated answer for example["query"]
    """
    stat_result = score_statistical(answer, example)
    judge_result = score_with_judge(example["query"], context_used, answer)

    return EvaluationReport(
        example_id=example["id"],
        target_system=example["target_system"],
        query=example["query"],
        answer=answer,
        statistical=asdict(stat_result),
        faithfulness_score=judge_result.faithfulness_score,
        faithfulness_reasoning=judge_result.faithfulness_reasoning,
        relevance_score=judge_result.relevance_score,
        relevance_reasoning=judge_result.relevance_reasoning,
        faithfulness_passed=judge_result.faithfulness_score >= config.FAITHFULNESS_PASS_THRESHOLD,
        relevance_passed=judge_result.relevance_score >= config.RELEVANCE_PASS_THRESHOLD,
    )
