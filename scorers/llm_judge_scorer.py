"""
LLM-as-judge scorer: uses an LLM to grade faithfulness and relevance
against the explicit rubric in docs/scoring_rubric.md.

Why an LLM judge at all, given statistical_scorer.py exists: keyword
matching can't tell you whether a claim is actually *supported* by the
retrieved context, or whether an answer that uses none of the expected
keywords is still a perfectly good answer phrased differently. The judge
reads the actual context and answer and reasons about it - at the cost of
being non-deterministic and needing calibration (see docs/judge_calibration.md,
written once you've validated it against a human-labeled subset).

Design choice worth defending in an interview: the judge always returns
structured JSON with a "reasoning" field, not a bare number. A score with
no reasoning is unauditable - you can't tell if the judge is scoring
consistently or just guessing.
"""

import json
from dataclasses import dataclass
from groq import Groq
import config

client = Groq(api_key=config.GROQ_API_KEY)

RUBRIC_TEXT = """
FAITHFULNESS (1-5): Does every factual claim in the answer trace back to the retrieved context?
5 = every claim supported, no unsupported additions.
4 = supported, one minor plausible elaboration beyond context.
3 = mostly supported but at least one unverified claim.
2 = contains a claim that contradicts the context.
1 = substantially fabricated or contradicts context on a material point.

RELEVANCE (1-5): Does the answer address the question asked, at the right level of specificity?
5 = directly and completely answers the question.
4 = answers it with minor tangential content.
3 = partially answers, or answers a related-but-different question.
2 = mostly off-topic.
1 = does not address the question at all.
"""

JUDGE_SYSTEM_PROMPT = f"""You are a strict evaluation judge for an AI fitness platform's outputs.
Score the given answer using EXACTLY this rubric:

{RUBRIC_TEXT}

Respond with ONLY a JSON object in this exact shape, no other text:
{{"faithfulness_score": <int 1-5>, "faithfulness_reasoning": "<one sentence>",
  "relevance_score": <int 1-5>, "relevance_reasoning": "<one sentence>"}}
"""


@dataclass
class JudgeResult:
    faithfulness_score: int
    faithfulness_reasoning: str
    relevance_score: int
    relevance_reasoning: str


def score_with_judge(query: str, context_used: str, answer: str) -> JudgeResult:
    """
    query: the user's question
    context_used: whatever context the subject system retrieved/generated
                   from (e.g. RAG chunks, or the Research Agent's output)
    answer: the final answer produced by the subject system
    """
    user_prompt = f"""QUESTION: {query}

CONTEXT USED BY THE SYSTEM: {context_used}

ANSWER TO EVALUATE: {answer}"""

    response = client.chat.completions.create(
        model=config.JUDGE_MODEL,
        temperature=config.JUDGE_TEMPERATURE,
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    raw = response.choices[0].message.content.strip()
    # Defensive parsing: judges occasionally wrap JSON in markdown fences
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Judge did not return valid JSON: {raw}") from e

    return JudgeResult(
        faithfulness_score=int(parsed["faithfulness_score"]),
        faithfulness_reasoning=parsed["faithfulness_reasoning"],
        relevance_score=int(parsed["relevance_score"]),
        relevance_reasoning=parsed["relevance_reasoning"],
    )
