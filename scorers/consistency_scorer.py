"""
Consistency scorer: compares two answers produced for a paraphrased pair
of queries (see golden_dataset.json's "consistency_pairs").

Why this is a separate file from llm_judge_scorer.py even though both call
an LLM: the input shape is fundamentally different (two answers being
compared to each other, not one answer against context), and the rubric
is different too. Keeping it separate keeps each file's responsibility
single and testable.
"""

import json
from dataclasses import dataclass
from groq import Groq
import config

client = Groq(api_key=config.GROQ_API_KEY)

CONSISTENCY_RUBRIC = """
CONSISTENCY (1-5): Do two answers to equivalent/paraphrased questions agree with each other?
5 = fully consistent, factual claims match.
4 = consistent in substance, differs only in phrasing/detail level.
3 = partial overlap, includes a claim not present (but not contradicted) in the other.
2 = contains a claim that mildly conflicts with the other answer.
1 = directly contradicts the other answer.
"""

CONSISTENCY_SYSTEM_PROMPT = f"""You are comparing two AI-generated answers to paraphrased versions of the same question, to check for contradictions.

{CONSISTENCY_RUBRIC}

Respond with ONLY a JSON object in this exact shape, no other text:
{{"consistency_score": <int 1-5>, "consistency_reasoning": "<one sentence>"}}
"""


@dataclass
class ConsistencyResult:
    consistency_score: int
    consistency_reasoning: str


def score_consistency(query_a: str, answer_a: str, query_b: str, answer_b: str) -> ConsistencyResult:
    user_prompt = f"""QUESTION A: {query_a}
ANSWER A: {answer_a}

QUESTION B (paraphrase of A): {query_b}
ANSWER B: {answer_b}"""

    response = client.chat.completions.create(
        model=config.JUDGE_MODEL,
        temperature=config.JUDGE_TEMPERATURE,
        messages=[
            {"role": "system", "content": CONSISTENCY_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    raw = response.choices[0].message.content.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Judge did not return valid JSON: {raw}") from e

    return ConsistencyResult(
        consistency_score=int(parsed["consistency_score"]),
        consistency_reasoning=parsed["consistency_reasoning"],
    )
