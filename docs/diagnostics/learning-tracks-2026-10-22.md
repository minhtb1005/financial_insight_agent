# Curriculum implementation and verification — 2026-10-22

## Delivered

- Main curriculum: 56 personal-finance lessons; optional market literacy: 10 lessons in 5 modules, freely accessible. Charts support budgeting, purchasing power and historical-price interpretation. M8L10 links the two tracks.
- Canonical catalog exported to frontend; lesson links preserve validated track/lesson through login and chat. Browser history and charts are isolated by learning context.
- Backend binds only allowed tools and checks again before execution/cache access. Market symbols must come from the current question or active chart, not a lesson example. Conceptual investment education remains allowed.
- Separate evaluation datasets: 68 personal-finance cases / 14 market-literacy cases. Original datasets preserved as historical diagnostics; no combined curriculum score. Runner records attempted and executed calls, saves progress, leaves semantic grading pending.
- Fixed TNCN/other educational abbreviations incorrectly rejected as tickers; company overview retrieval; OHLCV chart fetching; silent metric substitution; independent chart series; scoped LLM binding cache and 45-second provider-request timeout.

## Local evidence

- Focused backend regression suite: **119 passed** (API, agent, scope, chart tools, education calculators, company service, LLM providers).
- Follow-up after final cache/evaluator changes: **33 passed**, including blocked-tool selection counted as an evaluation failure and timeout forwarding through fallback.
- Frontend: production build passed; TypeScript and targeted ESLint passed; **6 Node tests passed**.
- Both datasets validate with complete lesson coverage; frontend export matches the canonical catalog.
- These are focused checks, not a claim that the entire repository test suite or all 82 live model cases passed.

## Live trace evidence

Local reports/logs reside under `frontend/artifacts/` (diagnostic artifacts, not benchmark baselines).

- `curriculum-market-initialized.json`: completed three cases. VNM six-month chart produced **126 observations**; missing-symbol question requested a symbol. Automated checks passed under the earlier checker.
- Manual inspection found a material teaching error in that earlier VNM response: it labeled unverified raw prices as VND. **Do not count that response as semantically correct.** Chart annotations and teaching instructions now explicitly require acknowledging unverified units without inventing a conversion.
- The abstract P/E question caused unnecessary stock-specific lookup using a lesson example. Added the symbol-provenance guard; offline regression verifies that call is blocked. The updated evaluator also reports invalid selections even when execution is blocked.
- Earlier core runs produced calculator/chart results but stalled in subsequent model calls. Added per-provider request timeout; this is not a strict end-to-end 45-second deadline because retries/fallback may add time.
- `curriculum-core-final.json`: completed budget case; all automated checks passed, exact 6m/3.6m/2.4m chart values, 33.5s. Manual review found inconsistent prose: “reduce savings” followed by examples retaining 20%, plus an unjustified universal minimum savings rate. Added explicit arithmetic/prose consistency guidance and a warning against mandatory ratios; do not treat this first response as a semantic pass.
- `curriculum-core-reviewed-prompt.json`: follow-up completed in **15.0s**, all automated checks passed. Spot review confirmed the inconsistent percentage example and universal savings minimum were absent. This spot review is not an independent full rubric grade.
- `curriculum-market-final.json`: completed **3/3 automated passes**. VNM chart recovered from a price-service timeout on retry, returned **123 observations**, and acknowledged unknown units (104.3s total). Missing-symbol case asked for the symbol with no tool call (3.2s). P/E case used only knowledge search, no guessed-ticker data call or buy order (28.0s). The P/E narrative still needs independent factual review; passing tool-scope checks does not certify the teaching.
- The final smoke runs use actual configured providers, but invoke the agent directly; they are not a browser or HTTP deployment test. Initial approval-quota failure was resolved; the later runs were authorized and completed.
- `running` or `incomplete` reports are unfinished and must not be published as pass rates. Full independent semantic review and held-out paraphrase evaluation remain outstanding.

## Operating notes

Restart API and standalone MCP after updating schemas; restart the frontend production server after building. Existing conversational server memory is still a no-op; the change isolates namespaces but does not restore general memory. Source price units and corporate-action adjustment status remain unverified when the upstream payload omits them.

Reproduce selected live checks with the configured model/data providers:

```powershell
$env:LANGCHAIN_TRACING_V2='false'
$env:LANGSMITH_TRACING='false'
.\.venv\Scripts\python.exe evals/run_curriculum_eval.py --ids personal_finance:budget_chart --output frontend/artifacts/curriculum-core-final.json
.\.venv\Scripts\python.exe evals/run_curriculum_eval.py --track market_literacy --ids market_literacy:MK2L1 market_literacy:no_symbol market_literacy:buy_advice --output frontend/artifacts/curriculum-market-final.json
```

See [architecture](../learning-tracks.md) and [evaluation protocol](../../evals/curriculum/v2/README.md).
