# Design Doc: AI Evaluation & Guardrails Platform

## What this is

A platform that scores AI-generated outputs (faithfulness, relevance,
consistency) and enforces guardrails (prompt injection, PII disclosure,
unsafe content) across three real subject systems: FitConnect's RAG-backed
Q&A, its Coach Agent, and its 4-agent LangGraph multiagent pipeline.

## Why LLM-as-judge over pure statistical scoring

Statistical scorers (keyword matching, ROUGE) are fast and deterministic
but can't tell whether a claim is actually *grounded* in retrieved context,
or whether a well-phrased answer using none of the expected keywords is
still correct. An LLM judge reads the actual context and answer and reasons
about it - at the cost of being non-deterministic and needing calibration
(see `docs/judge_calibration.md`). This project runs both: statistical
scorers as a free pre-filter, LLM judge for the nuanced call.

## Real findings from evaluating the actual FitConnect systems

This project was run against the real deployed systems, not synthetic
mocks, which surfaced genuine issues:

- **RAG relevance failures on real endpoints.** Several `rag`-tagged
  examples (`easy_003`, `edge_003`, `edge_005`, `easy_007`) scored
  faithfulness=5 but relevance=1-2. Investigation traced this to the RAG
  service being briefly unreachable (`FitnessQAService`'s fallback message
  "temporarily unavailable" being scored, correctly, as irrelevant), and
  separately to the fact that `/dashboard/ask` doesn't expose retrieved
  context to the client, limiting faithfulness scoring to the judge's
  general knowledge rather than true grounding verification.
- **A Coach Agent adversarial case (`adversarial_002`, a cross-user data
  request) scored faithfulness=1, relevance=1** - worth a closer look at
  whether the agent handled the boundary correctly or just answered
  off-topic; this is exactly the kind of case a guardrail-focused eval
  suite is meant to catch.
- **The deployed multiagent pipeline failed under evaluation load with a
  real 500 error**, traced (via Render logs) to a Groq `429` rate limit on
  `openai/gpt-oss-20b` - both tokens-per-minute and, on a later run,
  tokens-per-day. The pipeline has no retry/backoff for transient upstream
  failures, so a rate limit becomes a hard crash rather than a graceful
  retry. Mitigated in the eval client with retry-with-backoff
  (`integrations/multiagent_adapter.py`), but the underlying pipeline
  itself would benefit from the same treatment.
- **Shared model quota is a real constraint**, not just a local dev
  annoyance: the eval judge and the multiagent pipeline both drawing from
  the same Groq model's daily token budget caused cascading failures
  during evaluation. Fixed by using separate models/keys for judging vs.
  generation.

## Known limitations

- **Faithfulness scoring is weaker for RAG and Coach Agent than for the
  multiagent pipeline**, because neither of the first two exposes its
  retrieved context/internal reasoning to the client - `context_used` is
  empty for those adapters. The judge falls back to general-knowledge
  plausibility rather than true grounding verification. Fixing this
  properly would require exposing retrieved chunks (RAG) or
  stats/messages used (Coach Agent) from the backend for evaluation
  purposes.
- **The Coach Agent's endpoint is stateful and unparameterized**
  (`GET /communities/{id}/ai-coach`, no request body) - golden dataset
  queries for this system are scenario labels, not literal input, so
  reproducing a scenario requires manually seeding the test account's
  real stats/activity to match. This limits how easily new Coach Agent
  test cases can be added without manual setup.
- **Judge calibration is a one-time-per-model-change task**, not a
  permanent guarantee - if the judge model changes, `judge_calibration.md`'s
  process should be re-run.
- **Guardrail pattern lists (injection phrases, unsafe keywords) are
  deliberately coarse** - a real deployment should pair this with a
  proper moderation model (e.g. Llama Guard) rather than relying on
  keyword lists alone, which are straightforward to bypass with rephrasing.

## What I'd do differently at scale

- Separate Groq API keys/quotas per subject system and for the judge, to
  avoid the cascading rate-limit failures observed during evaluation.
- Run evaluations asynchronously/in parallel with per-service rate
  limiting, rather than sequentially, to reduce total run time without
  increasing burst load on any single quota.
- Expose retrieved context from RAG and Coach Agent for genuine
  faithfulness grounding, rather than scoring against empty context.
- Move from a single `results/latest_run.json` snapshot to timestamped run
  history, enabling trend tracking across pipeline/prompt changes over
  time - the dashboard already has the visual space reserved for this.
- Add the retry-with-backoff pattern used in the eval client to the
  multiagent pipeline itself, so transient upstream failures don't
  surface as hard 500s to real users.