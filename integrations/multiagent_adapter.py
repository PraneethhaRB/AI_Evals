"""
Adapter for the multi-agent LangGraph pipeline, deployed at
https://fitness-agent-pipeline.onrender.com/generate-plan.

Includes retry-with-backoff: this pipeline makes 4 sequential/parallel Groq
calls per request, so transient upstream rate limits (429s, surfaced by the
pipeline as 500s) are common under eval load, not a sign of a broken
request. Retrying once or twice with a short wait resolves most of these
without masking a genuinely broken request (which will still fail after
retries and get logged as a real ADAPTER_ERROR).
"""

import time
import requests
import config

MAX_RETRIES = 2
RETRY_WAIT_SECONDS = 25  # Groq's error message reports ~21s until quota resets


def get_answer(query: str) -> tuple:
    url = f"{config.MULTIAGENT_PIPELINE_URL}/generate-plan"

    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = requests.post(
                url,
                json={"goal": query},
                timeout=config.MULTIAGENT_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            data = response.json()

            answer = data.get("plan", "")
            context_used = ""

            if not answer:
                raise ValueError(f"Multiagent pipeline returned no plan field: {data}")

            return context_used, answer

        except requests.exceptions.RequestException as e:
            last_error = e
            is_last_attempt = attempt == MAX_RETRIES
            if not is_last_attempt:
                print(f"  [retry] multiagent_pipeline attempt {attempt + 1} failed "
                      f"({e}), waiting {RETRY_WAIT_SECONDS}s before retry...")
                time.sleep(RETRY_WAIT_SECONDS)

    return "", f"[ADAPTER_ERROR: multiagent_pipeline unreachable after {MAX_RETRIES + 1} attempts - {last_error}]"