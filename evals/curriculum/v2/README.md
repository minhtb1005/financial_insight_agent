# Curriculum benchmark v2

Primary: `personal_finance.jsonl` — 68 cases, all 56 core lessons.
Optional: `market_literacy.jsonl` — 14 cases, all 10 market-literacy lessons.

Run from repository root with the existing virtual environment:

```powershell
.\.venv\Scripts\python.exe evals/run_curriculum_eval.py --validate-only
.\.venv\Scripts\python.exe evals/run_curriculum_eval.py --track market_literacy --validate-only
.\.venv\Scripts\python.exe evals/run_curriculum_eval.py --limit 3
.\.venv\Scripts\python.exe evals/run_curriculum_eval.py --track market_literacy --limit 3
```

Omit `--limit` for a full live run (uses configured model/data providers). `--ids` selects full case IDs; `--output` chooses the report path. Each run contains exactly one track. No cross-track aggregate or comparison with the old stock baseline is valid.

The runner initializes the same service container as the API, records attempted tool selection separately from execution, and writes a checkpoint after each case. A report marked `running`/`incomplete` is not a completed run. Tool-result previews are truncated to 6,000 characters; chart payloads are retained. Run with `LANGCHAIN_TRACING_V2=false` and `LANGSMITH_TRACING=false` if external tracing is not wanted.

Every case maps to a real lesson and includes a human-review rubric. The 56 core lesson cases reuse authored curriculum questions to verify coverage; these are **development examples, not a held-out generalization test**. Boundary cases add missing inputs, scope injection, conceptual investment questions, fees, fraud and numeric fixtures. Add independently authored hidden paraphrases before claiming production quality.

Automated checks measure response presence, stream errors, tool scope, required/forbidden tools, chart count and explicitly specified chart values. Budget gold values are 12m × 50/30/20; purchasing power gold uses 100m × (1.06/1.04)^5. These fixtures are independent constants, not service-generated market truth. A valid schema or answered query is not evidence of correct teaching.

For each run, reviewers score each rubric item 0 (wrong/missing), 1 (partial), 2 (correct and clear), and record evidence from the answer. Review factual correctness, interpretation, useful exercise, sources/assumptions and respect for the product scope. Reports deliberately leave `semantic_review.status=pending` and `scores=null` until a reviewer does this; there is no automatic keyword-based teaching score. Never publish automated pass rate as curriculum quality.

Live market values can change. Verify the provider, returned dates, units and whether prices are adjusted; no fixed numerical market answer is claimed. Missing upstream data must remain visible as a failed/unavailable data case rather than fabricated successful output. Error/retry behavior is additionally covered by offline API/tool regression tests.

Legacy seeds were **rewritten** to serve learning outcomes: company profile (`comp_002`) → MK1L2; chart (`candle_001`) → MK2L1; ratio interpretation (`ratio_001`) → MK4L2. The original datasets and baseline stay unchanged for historical diagnostics. They do not determine the score of either curriculum track.
