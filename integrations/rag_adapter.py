"""
Adapter for FitConnect's RAG-backed fitness Q&A: POST /dashboard/ask.

Confirmed response shape (from DashboardController.java + the frontend's
own res.data.data usage): ApiResponse<String>, so the answer is a plain
string directly under the "data" key.

Note: this endpoint routes through FitnessQAService, which internally
proxies to a separate RAG microservice on port 8001 - the eval pipeline
never talks to that port directly, it only ever calls this authenticated
Spring Boot endpoint, same as a real user would.
"""

import requests
import config


def get_answer(query: str) -> tuple:
    url = f"{config.FITCONNECT_BASE_URL}/dashboard/ask"
    headers = {"Authorization": f"Bearer {config.TEST_USER_JWT}"}

    try:
        response = requests.post(
            url,
            json={"question": query},
            headers=headers,
            timeout=config.SUBJECT_SYSTEM_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()

        answer = data.get("data", "")  # confirmed: ApiResponse<String> -> plain string
        # No retrieved-chunks field is exposed to the client by this
        # endpoint, so context_used is left empty. Faithfulness scoring
        # for this system relies on the judge's general fitness knowledge
        # rather than a direct context comparison, unless you later expose
        # the retrieved chunks from FitnessQAService for eval purposes.
        context_used = ""

        if not answer:
            raise ValueError(f"RAG endpoint returned no data field: {data}")

        return context_used, answer

    except requests.exceptions.RequestException as e:
        return "", f"[ADAPTER_ERROR: rag_service unreachable - {e}]"