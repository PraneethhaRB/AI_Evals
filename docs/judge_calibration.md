# Judge Calibration

Validates whether `scorers/llm_judge_scorer.py`'s scores actually agree with
human judgment, before trusting it at scale.

## Why this matters

An LLM judge can be systematically miscalibrated in ways that are invisible
until you check: too lenient (inflates faithfulness/relevance across the
board), too harsh, or inconsistent between runs on the same input. Without
this check, every score this project produces is an unverified claim.

## Method

1. Pick 10-15 examples from `dataset/golden_dataset.json`, spanning easy,
   edge, and adversarial categories, and all three target systems.
2. Run each through `scorers/pipeline.py` to get the judge's
   faithfulness/relevance scores and reasoning.
3. Independently, score the same (query, context, answer) triples yourself
   by hand using the exact rubric in `docs/scoring_rubric.md` - without
   looking at the judge's scores first, to avoid anchoring your own
   judgment to its output.
4. Compare: for each example, record judge_score vs human_score for both
   dimensions.
5. Compute simple agreement: how many examples had judge and human scores
   within 1 point of each other? Flag any example with a gap of 2+ points
   for closer inspection - read the judge's reasoning for that example and
   decide whether the rubric wording needs to be sharper, or the judge is
   just wrong on that case.

## Recording results

Keep a simple table (add to this file as you go):

| Example ID | Dimension | Judge Score | Human Score | Gap | Notes |
|---|---|---|---|---|---|
| easy_001 | faithfulness | 5 | 5 | 0 | agree |
| edge_002 | relevance | 4 | 2 | 2 | judge missed the conflicting-goals framing |

## What to do with disagreements

- **Judge too lenient on a specific pattern** (e.g. always scores 5 when
  context is empty, as observed during real eval runs where `context_used`
  is often `""` for the RAG/Coach Agent adapters) - sharpen the judge
  prompt to explicitly handle the empty-context case rather than silently
  defaulting to a high score.
- **Judge and human disagree on genuinely ambiguous cases** - this is
  normal and doesn't mean the judge is broken; note it as a known
  limitation rather than chasing 100% agreement, which isn't a realistic
  bar even for two human raters.
- **Systematic bias in one direction** - if the judge is consistently
  1+ point higher or lower than human scores across most examples,
  consider adjusting `FAITHFULNESS_PASS_THRESHOLD`/`RELEVANCE_PASS_THRESHOLD`
  in `config.py` to compensate, and document why in the design doc.

## Known limitation

The judge model (`llama-3.3-70b-versatile` or similar via Groq) may share
blind spots with the systems it's evaluating if they use models from the
same family. Where feasible, use a different model/provider for judging
than for generation.