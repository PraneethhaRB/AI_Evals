# AI Evaluation & Guardrails Platform

A system for scoring and guarding LLM/RAG/agent outputs across faithfulness,
relevance, and consistency, with pre/post guardrails against prompt
injection, PII leakage, and unsafe content. Built to evaluate and improve
[FitConnect](#)'s RAG pipeline and multi-agent system.

## Why this exists

Most AI projects stop at "it generates an answer." This project answers the
next question: **how do you know the answer is any good, and how do you catch
it when it isn't?** It was built to evaluate real subject systems (FitConnect's
embedding-based RAG pipeline and 4-agent LangGraph workflow), not just as a
standalone demo.

## Architecture

```
Subject System (RAG / agents)
        |
        v
Evaluation Engine ---- Golden Dataset (dataset/golden_dataset.json)
   |         |
Scorers   Guardrails
(scorers/) (guardrails/)
        |
        v
   Dashboard (dashboard/)
```

## Project structure

```
dataset/      Golden Q&A dataset (easy / edge / adversarial cases)
scorers/      Statistical + LLM-as-judge scorers (faithfulness, relevance, consistency)
guardrails/   Input guardrails (injection, PII, off-topic) and output guardrails
              (hallucination gate, toxicity, PII disclosure)
api/          FastAPI service exposing evaluation endpoints
dashboard/    React dashboard for score trends and failing-case drill-down
tests/        Unit tests for scorers and guardrails (tested against known-good/bad examples)
docs/         Scoring rubric, judge calibration notes, design doc
```

- [x] Phase 1: Golden dataset + scoring rubric
- [x] Phase 2: Scoring engine (statistical + LLM-as-judge + consistency)
- [x] Phase 3: Guardrails layer (input: injection/scope, output: hallucination gate/PII/unsafe content)
- [x] Phase 4: Integration with real FitConnect RAG, Coach Agent, and multiagent pipeline (live services, not mocks)
- [x] Phase 5: Dashboard (FastAPI + React/recharts)
- [x] Phase 6: Tests for scorers, Docker, judge calibration methodology, design doc

## Real findings from evaluating live systems

This eval suite was run against FitConnect's actual deployed services and
surfaced genuine issues - not just passing scores. See
`docs/design_doc.md` for the full writeup, including a Groq rate-limit
failure traced through Render logs, and a RAG relevance pattern traced to
a backend outage.

## Running everything with Docker

```bash
docker compose up --build
```
API on `:8000`, dashboard on `:5173`.

## Running tests

```bash
pytest tests/ -v
```

## Running Phase 2 right now

```bash
cp .env.example .env        # add your real GROQ_API_KEY
pip install -r requirements.txt
python scripts/run_eval.py
```

This runs every example in the golden dataset through the statistical and
LLM-judge scorers using a **placeholder** subject system (see the docstring
in `scripts/run_eval.py`) so you can see real scores before Phase 4 wires in
your actual FitConnect systems.
