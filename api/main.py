"""
Minimal API layer: serves the contents of results/latest_run.json to the
dashboard. Deliberately thin - it has one job. If you later want run
history instead of just the latest run, this is the file to extend
(e.g. save timestamped files instead of always overwriting latest_run.json,
then add a /results/history endpoint here).
"""

import json
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="AI Eval Pipeline API")

# The dashboard runs on a different port (Vite's default 5173) than this
# API (8000) during local dev, so the browser blocks the request unless
# CORS explicitly allows it. Restricting to localhost origins only -
# tighten further if this is ever deployed publicly.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["GET"],
    allow_headers=["*"],
)

RESULTS_PATH = "results/latest_run.json"


@app.get("/api/results")
def get_results():
    if not os.path.exists(RESULTS_PATH):
        raise HTTPException(
            status_code=404,
            detail="No results found - run `python scripts/run_eval.py` first.",
        )
    with open(RESULTS_PATH, "r") as f:
        return json.load(f)