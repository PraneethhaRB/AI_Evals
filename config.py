"""
Central configuration for the evaluation pipeline.

Why this file exists: scoring thresholds and model choices should never be
hardcoded inside scorer logic. Keeping them here means you can tune
"what counts as a pass" without touching scoring code - and it's the file
you'll point to in an interview when asked "how would you make this
configurable for a different project."
"""

import os
from dotenv import load_dotenv

load_dotenv()

# --- LLM judge settings ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
JUDGE_MODEL = "openai/gpt-oss-20b"  # matches the multiagent_pipeline's model choice

JUDGE_TEMPERATURE = 0.0  # deterministic-as-possible scoring; judges should not be creative

# --- Guardrail / pass thresholds ---

FAITHFULNESS_PASS_THRESHOLD = 3   # below this, hallucination guardrail fires (Phase 3)
RELEVANCE_PASS_THRESHOLD = 3
CONSISTENCY_PASS_THRESHOLD = 3

# --- Statistical scorer settings ---
ROUGE_TYPE = "rougeL"
# --- Guardrail settings ---
# Fast pattern-based injection detection - obvious attempts, checked first
INJECTION_PATTERNS = [
    "ignore previous instructions",
    "ignore your instructions",
    "ignore the above",
    "system prompt",
    "you are now",
    "disregard your",
    "reveal your instructions",
    "act as my",
    "as my personal doctor",
    "as my doctor",
    "pretend you are",
]

# Query must relate to at least one of these to be considered in-scope.
# Deliberately broad - this is a recall-oriented allowlist, not a strict filter.
IN_SCOPE_KEYWORDS = [
    "workout", "exercise", "training", "fitness", "nutrition", "diet", "meal",
    "protein", "muscle", "weight", "community", "goal", "coach", "plan",
    "recovery", "injury", "cardio", "strength", "fitconnect", "account",
    "password", "login", "chat", "message", "admin", "join", "member",
]

# Simple PII patterns for output-side disclosure detection
PII_REGEX_PATTERNS = {
    "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "phone": r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b",
}

# Phrases that indicate the system is directly stating sensitive data,
# used alongside PII_REGEX_PATTERNS
PII_DISCLOSURE_PHRASES = [
    "password is", "email is", "their email", "their password",
]

# Minimal unsafe-content keyword list for a fast pre-filter.
# NOTE: a real deployment should pair this with a proper moderation model
# (e.g. Llama Guard) - keyword lists alone are easy to bypass and this is
# explicitly a coarse first layer, not the final word.
UNSAFE_CONTENT_KEYWORDS = [
    "kill yourself", "suicide method", "how to hurt",
]# --- Subject system service URLs (Phase 4) ---
# --- Subject system service URLs (Phase 4) ---
FITCONNECT_BASE_URL = os.getenv("FITCONNECT_BASE_URL", "http://localhost:8080")
MULTIAGENT_PIPELINE_URL = os.getenv(
    "MULTIAGENT_PIPELINE_URL", "https://fitness-agent-pipeline.onrender.com"
)

SUBJECT_SYSTEM_TIMEOUT_SECONDS = 30
MULTIAGENT_TIMEOUT_SECONDS = 120
RAG_TIMEOUT_SECONDS = 60  # Railway free tier can cold-start similarly to Render
# JWT for a dedicated test account, used by adapters that hit authenticated
# FitConnect endpoints (Coach Agent, RAG /dashboard/ask). Get this by
# logging in as your test user and copying the token from the login response.
TEST_USER_JWT = os.getenv("TEST_USER_JWT", "")
TEST_COMMUNITY_ID = os.getenv("TEST_COMMUNITY_ID", "1")