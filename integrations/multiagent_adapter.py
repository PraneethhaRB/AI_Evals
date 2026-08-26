"""
Adapter for the multi-agent LangGraph pipeline, deployed at
https://fitness-agent-pipeline.onrender.com/generate-plan (confirmed from
the real frontend fetch call).
"""

import requests
import config


def get_answer(query: str) -> tuple:
    """
    Returns (context_used, answer).

    Confirmed request/response shape from the real frontend code:
      POST /generate-plan  body: {"goal": query}  -> response: {"plan": "..."}

    NOTE: the response only exposes `plan` to the frontend - there's no
    separate research-summary field available here. That means the
    faithfulness judge has no independent context to check the plan
    against, only the plan text itself. context_used is left empty with
    this noted rather than faked. If your FastAPI service internally
    returns more fields (e.g. a research summary) that the frontend just
    isn't using, add that field name here to get real faithfulness scoring.
    """
    url = f"{config.MULTIAGENT_PIPELINE_URL}/generate-plan"

    try:
        response = requests.post(
            url,
            json={"goal": query},
            timeout=config.SUBJECT_SYSTEM_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()

        answer = data.get("plan", "")
        context_used = ""  # see note above - not exposed by this endpoint

        if not answer:
            raise ValueError(f"Multiagent pipeline returned no plan field: {data}")

        return context_used, answer

    except requests.exceptions.RequestException as e:
        return "", f"[ADAPTER_ERROR: multiagent_pipeline unreachable - {e}]"