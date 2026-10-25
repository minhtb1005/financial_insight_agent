# Learning tracks and tools

Personal finance remains the main product: 10 modules / 56 lessons. The optional market-literacy track has 5 modules / 10 lessons about ownership, historical charts, returns/risk, financial statements and evidence. Anyone can open it; completion of the core track is recommended context, not an access gate. The learning objective is understanding and verification, not picking profitable trades.

Chart entry points: M1L1 (budget), M4L2 and M8L5 (purchasing power), M8L10 (bridge to markets), MK2L1–MK2L2 (historical stock charts). Optional lessons have short readings, exercises, questions and source links where relevant. The catalog is `src/application/learning/catalog.json`; run `python scripts/sync_learning_catalog.py` after edits. The tracked frontend export is checked with `--check`.

`POST /api/v1/ask-stream` accepts `learning_context: {track, lesson_id?}`. Default is `personal_finance`; unknown tracks, unknown lessons, cross-track lessons and client-supplied tool allowlists are rejected. The frontend preserves this scope through login and lesson-to-chat links. Browser history and memory namespaces are separated by user, track and lesson; switching aborts the previous stream and clears its charts. A lesson chat can be broadened by selecting its track name.

Core tools: budget, future value, loan schedule, PIT, rates, knowledge, learning chart. Market tools: historical price/chart, company profile, financial ratios and knowledge. Optional lessons narrow this further (e.g. MK1L1 only knowledge; MK2L1 price/chart). The model gets only these tool schemas; the action node checks the allowlist again before cache access/execution. Scope is in request/graph state, so concurrent requests cannot change each other's tools. It is a product scope, not account-level authorization for the standalone MCP service.

`AGENT_MODE` remains compatible for unscoped legacy Python callers. Public chat always supplies a validated learning scope; legacy full runs are explicit diagnostic paths. Forecast, indicator, ranking, portfolio, sentiment and alert code remains available for historical diagnostics but is not shown to the model in either learning track. It contributes no curriculum score.

Learning charts calculate explicit scenarios and label assumptions; they never query stock data. Market charts require symbols, fetch OHLCV, reject absent metrics, and never replace P/E with prices. Multi-series rendering aligns observations by x-value and keeps missing points missing. Price units and adjustment status remain unknown unless a source establishes them; chart text must not invent a VND conversion or claim total return or prediction.

The app has no restored short-term server memory; its existing memory manager's `add_interaction` is a no-op. Dashboard follow-ups retain a chart summary, while other underspecified follow-ups may need the learner to repeat details. This change does not claim to restore general conversation memory.

Evaluation instructions and limitations: `evals/curriculum/v2/README.md`.

Restart the API and standalone MCP server after updating so both expose the new chart/profile schemas; restart the frontend for a production build. `get_company_info(field="overview")` now retrieves the actual profile for MK1L2. Common curriculum abbreviations (TNCN, BHXH, OTP, etc.) are excluded from ticker detection; unknown explicit tickers are still checked. Symbols must come from the current query or active chart, not the sample question in a lesson.
