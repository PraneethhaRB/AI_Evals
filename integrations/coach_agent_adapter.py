"""
Adapter for FitConnect's Coach Agent: GET /communities/{communityId}/ai-coach
(assuming this controller is mounted at /communities - confirm the class-level
@RequestMapping if this 404s).

Confirmed response shape: ApiResponse<CoachResponse>, where CoachResponse =
{"message": str, "toolsUsed": [...], "iterationCount": int}.

IMPORTANT DESIGN NOTE: this endpoint takes NO request body - it generates
a coaching insight purely from the authenticated user's real stored stats
and community messages. The `query` text from the golden dataset is NOT
sent anywhere here; it exists only as a human-readable label for what
scenario you're supposed to have set up for the test account (e.g. for
easy_005 "I hit all my workouts this week", you need to have actually
logged those workouts for TEST_USER_JWT's account before running eval).
Document this as a known limitation in your Phase 6 design doc.
"""

import requests
import config


def get_answer(query: str) -> tuple:
    url = f"{config.FITCONNECT_BASE_URL}/communities/{config.TEST_COMMUNITY_ID}/ai-coach"
    headers = {"Authorization": f"Bearer {config.TEST_USER_JWT}"}

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=config.SUBJECT_SYSTEM_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()

        coach_response = data.get("data", {})  # confirmed: ApiResponse<CoachResponse>
        answer = coach_response.get("message", "") if isinstance(coach_response, dict) else ""
        # toolsUsed/iterationCount are available too if you later want to
        # score "did the coach actually use tools" as its own dimension.
        context_used = ""

        if not answer:
            raise ValueError(f"Coach Agent returned no message field: {data}")

        return context_used, answer

    except requests.exceptions.RequestException as e:
        return "", f"[ADAPTER_ERROR: coach_agent unreachable - {e}]"