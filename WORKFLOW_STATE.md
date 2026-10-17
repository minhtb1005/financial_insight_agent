# WORKFLOW_STATE.md — Source of Truth

## Request (gói mới — user chốt kiến trúc 10/09/2026, triển khai trước)
1. **Metric mới**: `retry_rate` + `wasteful_duplicate_rate` cho benchmark.
2. **Data pipeline**: pilot (4a) trước → full (4b) sau.
3. **RAG benchmark riêng** cho `search_knowledge` (dataset mới 40-60 cases).
4. **News sentiment**: nguồn free (`vnnews` + `vnewsapi` đều đánh giá) + sentiment 2 cách (LLM gpt-4o-mini, PhoBERT CPU-LoRA + benchmark as-is).

## Clarified Scope (Phase 2 — đã chốt đủ, gồm 2 xác nhận cuối 10/09/2026)
- Baseline model = `gpt-4o-mini` cho mọi đo mới; không đo song song GPT-4.1.
- Thứ tự: baseline chốt → (1) dup-tool metric → (4a) pipeline pilot → (2) RAG benchmark → (3) news sentiment → (4b) pipeline full.
- Metric: `retry_rate` (lặp ngay sau `TOOL_ERR#`, không tính waste) vs `wasteful_duplicate_rate` = duplicate-success-trước-đó / tổng tool_calls, mean per case, áp dụng cả agent 36 + dashboard 102; backfill free từ trace (`--samples-from`); chưa đặt ngưỡng, chạy lấy phân bố trước (tham khảo ≤5%).
- Pipeline 4a: ~15-20 mã trong golden cases, daily OHLCV + ratio fields, KHÔNG events; sqlite; `start_scheduler` in-app 10-20p; hiển thị freshness công khai.
- News: free only — spike so sánh `vnnews` vs `vnewsapi` trước khi chốt; chỉ lưu title+excerpt+link+date. LLM: gpt-4o-mini → `{label, score[-1,1], rationale}`. PhoBERT CPU-only: (a) benchmark as-is `Marky12345/BigData_2026`, (b) LoRA/few-epochs/batch-nhỏ adapt nhẹ (wonrax hoặc visobert) trên vài trăm mẫu finance; so sánh accuracy/F1 trên tập nhãn tay 30-50 tin, đạt nếu trong ~5-10% với cost/latency thấp hơn nhiều.
- RAG: dataset mới 40-60 cases (8-12/tier × 5 tiers VBPL/TT/HNX-HOSE/SSI/quốc tế) + out-of-scope refusal cases; audit Qdrant trước khi viết case; metrics P@k/R@k + citation correctness chặt + refusal rate, tách khỏi RAGAS hiện có.
- Gate: mở rộng `compare_reports.py` (2%); benchmark-trước-merge mỗi phase; crawl kiểm soát + resumable chunk.

## Library verification (websearch 10/09/2026)
- `vnstock_news`: docs 21+ báo có thật; insider libs sponsor-gated → LOẠI (user chốt free).
- `vnnews` (thinh-vu, MIT): tồn tại nhưng bỏ hoang (2022, 1 star) → rủi ro, chỉ spike.
- `vnewsapi` (PyPI 01/2026, finance: CafeF/CafeBiz/VietStock…, RSS+sitemap+batch) → ứng viên free chính, spike so sánh.
- `wonrax/phobert-base-vietnamese-sentiment`: tồn tại (MIT, NEG/POS/NEU) nhưng train 30K e-commerce + đòi word-segmented → lệch domain, phải adapt + nhãn finance. `Marky12345/BigData_2026`, `5CD-AI/Vietnamese-Sentiment-visobert`: chưa verify — implementor verify tồn tại/license/labels trước khi dùng.

## Constraints
- Baseline `gpt-4o-mini`; không bịa số; tập nhãn tay cho news/RAG; chỉ excerpt tin; hiển thị freshness; crawl resumable; CPU-only cho PhoBERT.
- Planner: không sửa code ngoài WORKFLOW_STATE.md.

## Acceptance Criteria (per phase — xem Plan)

## Current Status
- **Lịch sử:** Phase 1 DONE (dup-metrics `retry_rate`/`wasteful_duplicate_rate`, backfill 2 runs: waste 0.000 cả hai; review PASS_WITH_FOLLOWUPS F1-F5). Phase 4a BUILD DONE (market_store sqlite 50.587 rows/15 mã, read-through + freshness 8 services, scheduler 15p, subset rerun numeric 1.000; ratios hoãn vì upstream hỏng).
- **Phase 2 + Phase 3 (song song, 10/09/2026) — multi-agent lần đầu chạy được (type `general`).**
- **Phase 2 RAG DONE (audit → dataset → runner → baseline):** audit Qdrant (cloud bị chặn egress; local migrate bit-for-bit sang `data/qdrant_local_v117` do client mới không đọc `meta.json` legacy; 33 docs/236 chunks, tier quốc tế trống) → `evals/golden/rag_dataset.jsonl` 46 cases (VBPL 6 + TT 10 + HNX-HOSE 12 + SSI 10 + 8 OOS) → `evals/run_rag_eval.py` + `evals/rag_metrics.py` + 25 tests pass. Baseline gpt-4o-mini: P@5 0.174 / R@5 0.868 / citation 1.0 / refusal 1.0 / false-refusal 0.079 / coverage 0.842 / 353ms. Đã verify: 36/36 tests pass, số khớp file nguồn, gate chạy được sau khi fix bug crash với metrics dict (`per_tier`, `citation_totals` → skip non-numeric). Phát hiện: `min_score=0.3` production lọc gần hết (top hit query tốt ~0.27) — cần quyết định ngưỡng riêng.
- **Phase 3 news DONE (10/09/2026)** — adapter + engines + default + e2e hoàn tất.
  - Root cause thật: `NewsAdapter` map sai cột VCI → 50 bài blank (đã fix mapping + test). Kiến trúc chốt: `CombinedNewsAdapter` (VCI-fixed chính + RSS phụ lấy excerpt, dedupe, drop blank) + alias tên công ty cho 15 mã pilot; wiring trong `dependencies.py` (fallback graceful).
  - Engines (`infrastructure/sentiment/engines.py`): LLM zero-shot structured `{label,score,rationale}` (sửa 2 bug: `with_structured_output` trả Groq trước khi fallback=False; json_mode đòi chữ "json" trong prompt) + HF lazy + keyword fallback (không bao giờ raise). Service xuất thêm `sentiment_detail`, giữ `sentiment` float cũ. Default: **HF PhoBERT** (F1 0.907 trong 7.1% so LLM 0.978, free/CPU/offline); LLM khi cần rationale (`SENTIMENT_ENGINE=llm`).
  - Số 3 chiều trên 45 nhãn: keyword 0.578/0.557, HF 0.911/0.907, LLM 0.978/0.978 (44/45, 0 failed). Env note: GROQ key 401 (fallback chain vẫn OK nhờ primary), eval script thiếu load_dotenv (đã fix).
  - E2E tin thật: VCB/60d 11 bài +0.179 pos; HPG/30d 0 bài là đúng (tin mới nhất 30/07 ngoài window), bỏ lọc 50 bài +0.431 pos. Hết sentiment-0-rỗng ở mã có tin.
  - Tests: 73 pass (sentiment+portfolio+api_clients; skips pre-existing). Caveat: nhãn tự viết → số chỉ báo; LLM 44/45 gợi ý tập nhãn còn dễ.
- Next: **Phase 4b outline** (mở rộng toàn sàn + intraday + postgres khi concurrent R/W).
- README: sections RAG + news mới (số đã verify khớp nguồn). `git status`: thêm rag_dataset, run_rag_eval, rag_metrics, test_rag_metrics, news labels, run_news_sentiment_eval, test_news_sentiment_pure, news_source_spike; sửa compare_reports.py + README.
- **Phase 4b OUTLINE DONE (10/09/2026)** — `docs/pipeline_full_outline.md`, không code (xem file).
- **REVIEW TỔNG THỂ (10/09/2026): full unit suite 637 passed / 43 failed / 48 skipped. 43 failed đều pre-existing** — chứng minh bằng `git stash` (baseline sạch fail y hệt): redis_cache 26, serialization 2, traces_api 6 (auth 401), circuit_breaker 1, infra_dependencies 2, cli_console 6. Không failure nào thuộc code mới/sửa.
- **Tests 2 tầng DONE (10/09/2026)** — Tầng 1: viết lại 48 skipped `legacy strict DI` bằng FakePort (alert 12, forecast 11, sector 10, portfolio 15; 0 marker skip còn lại, +2 tests mới) — 88/88 pass, 0 skipped. Kèm fix thật do test mới phát hiện: `sector ranked entries` rớt `data_as_of` khi rebuild dict (1 dòng). Tầng 2: `src/tests/integration/test_vnstock_contract.py` (10 tests, opt-in `RUN_LIVE_CONTRACT=1`, pacing 4s, assert shape + fixed-dates VCB/HPG/FPT/VNM/BID + cột news VCI + read-through + RSS reachable + upstream status) — live run: **9 passed, 1 skipped** (ratio upstream hỏng, skip có lý do; sẽ đỏ khi nguồn hồi phục là đúng). README: table entry + subsection 2 tầng. Suite tổng còn 43 failed pre-existing (đã chứng minh qua stash).
- **Ratio DB wiring DONE (10/09/2026, ngoài gói)**: `FinancialAdapter` chuyển sang `Finance.ratio()` VCI→KBS (root-cause: `Company.financial_statement()` không tồn tại trên 3.5.1) + `FinancialRatioService` DB-first qua `ratios_snapshot` (lan `data_as_of`/`data_source`, write-back khi miss) + `ingest_ratios.py` backfill/refresh resumable + job quý `ratios_refresh` + wiring `dependencies.py`. Tests mới 8 pass (adapter 2, parser 2, read-through 2, ingest 2); touched-areas 26 pass. Suite tổng: failures còn lại đều pre-existing/môi-trường (redis/bcrypt/feedparser/mcp/traces/cli — đã đối chiếu nguyên nhân, không file nào thuộc code mới). Live 3.5.1 vẫn hỏng cả 2 nguồn (VCI KeyError, KBS 404) → ingest live failed-graceful; next: upgrade vnstock v4 (VCI Finance REST mới) rồi backfill 15 mã.
- **Upgrade vnstock v4 + backfill live DONE (10/09/2026)**: venv `3.5.1 → 4.0.7`, pin `pyproject` `vnstock>=4.0.6` (+ cài thiếu `bcrypt/feedparser/python-jose`, pin `mcp>=1.9,<2` vì v2 bỏ `FastMCP`). Live verify: `Finance.ratio()` OK cả 2 nguồn — chốt **KBS chính** (tươi 2026-Q2/Q3), VCI fallback (stale 2018); `Quote.history` + `Company.news` không gãy. Live contract **10/10 pass** (ratio test trước skip, giờ xanh). Backfill ratios **15/15, 0 failed, 106 rows**; e2e 15/15 `pe` từ DB, 0 live call. Dọn 1 row rác `pe_ratio` do write-back từ test cũ + bịt bằng cách service không tự tạo store (DI tường minh từ `dependencies.py`). Suite tổng **694 passed / 43 failed** = khớp baseline pre-existing (redis/serialization/traces/circuit/infra_deps/cli).
- **43 pre-existing failures DỌN SẠCH (10/09/2026)**: unit suite **737 passed / 0 failed** (trước: 694/43), live contract 10/10 giữ nguyên. Chi tiết: serialization thiếu 2 methods → implement `get_compression_ratio`/`get_format_stats`; traces 6 × 401 → test fixture override admin auth; circuit `record_success` không reset counter ở CLOSED (bug thật) → reset; shutdown `isinstance(Protocol)` fail cả mock lẫn component duck-typed (bug thật, leak task) → duck-typing + spec mocks; redis 26 → `_connect` client-first + `_create_client` seam + `_guard_lock` lazy, `info()` thêm `redis_info`, test flush-all khớp guard an toàn; cli 6 → `/exit` propagate SystemExit + init-fail exit(1), test wording EN→VI. Venv bổ sung deps thiếu (`aiosqlite/alembic` cho traces). Không regression: vùng giá/ratio/market-store xanh hết.
- **Docker packaging DONE (10/09/2026, approach A fix-in-place)**: 6 services giữ nguyên (frontend/backend/mcp/postgres/redis/qdrant). Fix đã verify live: (1) compose ép `QDRANT_PATH=`/`QDRANT_URL=` rỗng (nếu không backend dùng nhầm embedded theo thứ tự ưu tiên trong code); (2) healthcheck MCP chuyển GET→POST initialize (GET trả 406, treo cả stack) + `start_period` 180s, backend 240s (cold boot torch); (3) bỏ healthcheck qdrant (image không có curl/wget, dash không /dev/tcp; không service nào gate vào nó); (4) volume share `app_data` cho sqlite (mcp đọc ké backend) — persist đã chứng minh sau `down` (105 ratios + 50587 prices); (5) `.dockerignore` mới; (6) `middleware.ts`→`proxy.ts` theo Next 16 (file cũ match-all redirect cả /api/health) + matcher public paths; (7) thêm `psycopg2-binary` (alembic cần sync driver) + pin `langchain-mcp-adapters<0.2` (0.2+ clash langchain-core 0.3) + pin `mcp<2`. Gate: backend healthy /health 200, frontend /api/health 200 agent_ready:true + /dashboard vẫn 307 về login, unit 737/0 giữ nguyên. Biết: WSL dockerd môi trường này restart liên tục (~10 phút) nên chưa chụp được khoảnh khắc all-green đồng thời; seed RAG collection trong qdrant service vẫn là việc tay (`rag.cli run --force`).
- Next: reviewer tổng thể hoặc đóng gói (phần còn lại).

## Plan (Approved-candidate — 5 phases, mỗi phase benchmark-trước-merge)

### Phase 1 — Dup-tool metrics (rẻ nhất, làm trước, không chạm agent)
1. Thêm `evals/metrics_duplicates.py` (mới, pure functions + unit test): parse tool spans theo thứ tự từ trace detail (fallback: tool-call records trong sample); normalize args (sort keys, làm tròn số) để so "giống nhau".
   - `retry_rate` = số calls mà call trước đó cùng key trả về `TOOL_ERR#` / tổng tool_calls.
   - `wasteful_duplicate_rate` = số calls trùng key với 1 call success trước đó / tổng tool_calls.
   - Per-case + mean; case 0 tool_calls → `None` (loại khỏi mean, ghi rõ).
2. Tích hợp vào `run_benchmark.py` (aggregate + per-case + report.md). Dashboard 90+12 ghi N/A + lý do (mock rows, không agent loop) thay vì ép số 0.
3. Backfill: chạy `--samples-from` trên cả 2 reports hiện có (`benchmark-rescore-20260825-043846`, `benchmark-rescore-20260910-024011`) — kiểm tra traces còn trong `data/traces/traces.db` trước; nếu thiếu thì báo, KHÔNG re-run agent vội.
4. Mở rộng `compare_reports.py`: thêm 2 metrics vào gate 2%.
5. README: định nghĩa công thức + bảng phân bố 2 runs (chưa chốt ngưỡng).
- Chấp nhận: metric chạy được offline, số khớp recompute thủ công ≥1 case/phase, gate hoạt động.

### Phase 4a — Pipeline pilot (giảm đau rate-limit ngay)
1. Audit: trích ~15-20 tickers + fields (daily OHLCV, ratio fields) từ 36+90 golden cases → `docs/pipeline_pilot_scope.md` (giữ ngắn).
2. Mới `src/infrastructure/market_store/`: schema sqlite (`prices_daily`, `ratios_snapshot`, `ingest_meta{source,fetched_at}`); ingest job chunked-resumable (tái dùng pattern orchestrate: chunk nhỏ + sleep, guest 20 req/phút); job refresh "today" 10-20p qua `start_scheduler` (log/metrics sẵn có).
3. Read-through ở service layer (DB trước, fallback vnstock khi miss/stale) — KHÔNG đổi interface tool; tool output + final answer kèm `data_as_of` (freshness công khai).
4. KHÔNG events. KHÔNG postgres. KHÔNG cron ngoài.
- Chấp nhận: pilot tickers phục vụ từ DB (log chứng minh hit-rate), rerun 1 subset benchmark không chết rate-limit, freshness hiển thị đúng, golden dataset re-validate sau khi đổi nguồn (đặc biệt case realtime/"today").

### Phase 2 — RAG benchmark (độc lập vnstock, làm song song được sau 4a)
1. Audit Qdrant: collections nào, bao nhiêu docs, nguồn nào trong 5 tiers — báo cáo trước khi viết case.
2. Mới `evals/golden/rag_dataset.jsonl` (40-60 cases, 8-12/tier) + nhóm out-of-scope (kỳ vọng từ chối, nối edge).
3. Mới `evals/run_rag_eval.py`: Retrieval P@k/R@k vs nhãn tay, citation correctness (citation trỏ đúng doc đã retrieve — chặt hơn citation_rate), refusal rate; baseline gpt-4o-mini.
4. Nối gate `compare_reports.py`; README section RAG riêng.
- Chấp nhận: chạy offline được, có baseline số, case out-of-scope đo được refusal.

### Phase 3 — News sentiment (sau khi có pipeline pattern + RAG xong)
1. Spike timebox ngắn: cài `vnnews` và `vnewsapi` vào venv thử nghiệm, fetch mẫu CafeF/VietStock, so sánh completeness (title/excerpt/link/date) + độ ổn định → decision record, chọn 1 (fallback RSS thuần nếu cả 2 tệ).
2. Adapter mới cho `NewsPort`: crawl theo ticker, chỉ lưu title+excerpt+link+date (+cache TTL).
3. Sentiment v1 (LLM gpt-4o-mini): `{label: pos/neu/neg, score: [-1,1], rationale}` thay `_classify_sentiment` keyword (giữ keyword làm fallback khi LLM fail).
4. Sentiment v2 (PhoBERT CPU-only, theo thứ tự tiết kiệm công): (a) benchmark as-is `Marky12345/BigData_2026` (verify tồn tại/license trước) — nếu đã đạt thì DỪNG, không adapt; (b) chỉ khi (a) chưa đạt mới LoRA + few epochs + batch nhỏ adapt (wonrax hoặc visobert) trên vài trăm mẫu finance; so accuracy/F1 trên tập nhãn tay 30-50 tin — đạt nếu trong ~5-10% so LLM với latency/cost thấp hơn nhiều.
5. Benchmark news cases (news_001/002 + thêm) hết rỗng trên tickers có tin.
- Chấp nhận: hết sentiment 0.0 rỗng ở tickers phủ sóng; cả 2 cách có F1 công bố; decision v1/v2 default rõ ràng.

### Phase 4b — Pipeline full (outline, plan chi tiết sau 4a)
- Mở rộng toàn sàn + intraday 2-3 năm + (events chỉ khi có tool consumer); migrate postgres khi concurrent R/W; cron ngoài khi nhiều replica. Không làm trong gói này ngoài outline.

### Thứ tự + gate chung
Baseline gpt-4o-mini → P1 → P4a → P2 → P3 → (P4b outline); mỗi phase: implement → benchmark so baseline → `compare_reports.py` gate → README cập nhật → mới sang phase tiếp. Dừng/escalate khi gate đỏ 2 lần liên tiếp.

## Files To Change (dự kiến theo phase)
- P1: mới `evals/metrics_duplicates.py` (+ unit test), sửa `evals/run_benchmark.py`, `evals/run_dashboard_eval.py`, `evals/compare_reports.py`, `README.md`.
- P4a: mới `src/infrastructure/market_store/*`, sửa service layer read-through (price/ratio), scheduler wiring, `docs/pipeline_pilot_scope.md`, `README.md`.
- P2: audit Qdrant (đọc), mới `evals/golden/rag_dataset.jsonl`, `evals/run_rag_eval.py`, sửa `compare_reports.py`, `README.md`.
- P3: spike deps (venv thử nghiệm), sửa `news_adapter.py`/`news_sentiment_service.py` (+ interface sentiment), mới eval nhãn tay 30-50 tin + script đo F1, `pyproject.toml` nếu chốt dep mới, `README.md`.
- P4b: outline trong `WORKFLOW_STATE.md`/docs (chưa code).
- Không sửa: `evals/baselines/baseline-v1.json`, `.env`.

## Request mới (14/10/2026 — NVIDIA migration, ưu tiên cao)
- OPENAI_API_KEY đã hỏng (rỗng trong `.env`); chuyển sang `NVIDIA_API_KEY`, `NVIDIA_API_KEY2`, `NVIDIA_API_KEY3`, `NVIDIA_CHAT_MODEL=nvidia/nemotron-3-ultra-550b-a55b`, `NVIDIA_EMBEDDING_MODEL=nvidia/nemotron-3-embed-1b` đã có trong `.env`.
- Thiết kế xoay key theo mỗi request (round-robin + fallback khi 429/401/5xx) để tiết kiệm quota và trải nghiệm mượt.
- Migrate embedding vector DB sang `NVIDIA_EMBEDDING_MODEL`; chưa cần chạy lại benchmark.
- Hiểu hiện tại: `LLMProvider` = `ChatOpenAI(gpt-4o-mini)` primary + `ChatGroq(llama-3.1-8b-instant)` fallback; `GROQ_API_KEY` trong `.env` sai format (sk-proj, đã 401 trước đây). `Embedder` = `OpenAI(text-embedding-3-small, dim 1536)` primary + `sentence-transformers e5-base dim 768` fallback; Qdrant collections hiện dim 1536; `sources.yaml` pin `text-embedding-3-small/1536`. Chưa có dep `langchain-nvidia`.

## Clarified Scope (Phase 2 — user chốt 14/10/2026)
- Chat: thay hẳn primary OpenAI → NVIDIA qua `ChatOpenAI(base_url=https://integrate.api.nvidia.com/v1, model=NVIDIA_CHAT_MODEL)`; **giữ Groq làm fallback**; giữ code/docs OpenAI (chưa xóa).
- Xoay key: tối giản, **không thêm dep mới** (`langchain-nvidia` loại). Cần thread-safe (+async-safe) round-robin trên 3 keys + skip-on-failure (429/401/5xx → thử key tiếp theo trong cùng request) + theo dõi quota/rate-limit cơ bản (đếm lỗi/throttle + cooldown, in-memory là đủ, không persist).
- Embedding: `Embedder` primary → NVIDIA (`OpenAI(base_url=..., model=NVIDIA_EMBEDDING_MODEL)`, **dim native 2048**), giữ OpenAI + sentence-transformers làm fallback sau. Tạo collection mới dim 2048 + swap alias `finsight_knowledge`, giữ collection cũ 1536 backup theo `cleanup_old_backups(7)`. Target **local `data/qdrant_local_v117`**. Được chạy ingest/re-embed thật bằng quota NVIDIA.
- Eval: **không chạy lại benchmark** (không `run_benchmark`/`run_rag_eval`/`run_ragas_eval` full); chỉ đổi default model string sang `NVIDIA_CHAT_MODEL` trong eval scripts + unit tests.
- Config: đưa `NVIDIA_*` vào `docker-compose.yml/dev`, `.env.example`, CI secrets. Giữ `OPENAI_*`.

## Library verification (websearch 14/10/2026)
- NVIDIA NIM hosted tại `https://integrate.api.nvidia.com/v1`, **OpenAI-compatible** (`/v1/chat/completions`, `/v1/embeddings`); dùng SDK `openai`/`ChatOpenAI(base_url=...)` + `model=nvidia/...` là pattern chính thức (build.nvidia.com/llms.txt + docs.api.nvidia.com).
- `nvidia/nemotron-3-ultra-550b-a55b`: reasoning MoE 550B/55B-active, tool-calling/agent được hỗ trợ qua OpenAI-compatible API; `temperature=0` + `max_tokens` tường minh (NVIDIA yêu cầu max-tokens rõ ràng, nếu không dễ 500).
- `nvidia/nemotron-3-embed-1b`: **dim native 2048** (BF16, Ministral-pruned, max_seq 32768); `dimensions` chỉ nhận 2048 (truyền giá trị khác → 400); hỗ trợ `input_type=query|passage` cho retrieval (nên dùng: query khi search, passage khi ingest — cần implementor verify thực tế vì OpenAI SDK có thể phải truyền qua `extra_body`).
- Qdrant: collection dim cố định lúc `create_collection` → bắt buộc collection mới 2048, không reuse 1536.

## Constraints
- Không thêm dep mới; reuse `LLMChain` fallback + `cleanup_old_backups(7)` + pipeline `run_full_refresh(force)` sẵn có.
- Thread-safe/async-safe KeyPool, in-memory (không persist counter).
- Không chạy benchmark full; chỉ unit + live smoke 1 chat + 1 embed.
- Planner: không sửa code ngoài WORKFLOW_STATE.md.

## Acceptance Criteria (NVIDIA migration)
1. Chat qua NVIDIA key xoay thành công (live smoke 1 call), key lỗi → tự thử key kế tiếp trong cùng request; Groq fallback còn nguyên.
2. Xoay key round-robin + cooldown có unit test (bao gồm thread-safety cơ bản).
3. Embedding NVIDIA trả vector dim 2048 (live smoke); collection mới 2048 được alias `finsight_knowledge` trỏ tới, collection cũ còn (backup); `sources.yaml` + manifest ghi đúng model/dim/provider.
4. `search_knowledge` trả hits trên collection mới (không dính lỗi dim-mismatch).
5. Eval scripts default sang `NVIDIA_CHAT_MODEL`; không benchmark full.
6. `docker-compose.yml/dev`, `.env.example`, CI workflow có `NVIDIA_*`; unit suite không regression.

## Plan (Approved sau debate 14/10/2026 — debater verdict REVISE, đã tiếp thu)
1. **KeyPool mới** `src/infrastructure/llm/nvidia_key_pool.py` (~60 dòng): đọc `NVIDIA_API_KEY/2/3` (bỏ rỗng), `threading.Lock` quanh đoạn ngắn (đủ cho sync+async, không `asyncio.Lock`), `get_next()` bỏ qua key đang cooldown (~60s, env-override) + `report_success/failure(key,status)` đếm 429/401/5xx. Dùng chung 1 pool cho chat + embed.
2. **Chat** `llm_provider.py`: mới `NVIDIARotatingChat` xoay key **per-invoke** (không per-bind): `with_structured_output`/`bind_tools` trả wrapper mới giữ (pool, tools/schema); mỗi `invoke` pick key → dựng `ChatOpenAI(base_url=NVIDIA_BASE_URL, api_key=key, model=NVIDIA_CHAT_MODEL, temperature=0, max_tokens=4096, max_retries=0)`; lỗi retryable/auth (classify theo `type(e).__name__` như `LLMChain`) → `report_failure` + thử key kế tiếp (tối đa len(keys) lần) rồi rơi sang Groq qua `LLMChain` hiện có. Sửa message lỗi `OPENAI→NVIDIA/GROQ`.
3. **Embedder** `embedder.py`: primary `OpenAI(base_url, model=NVIDIA_EMBEDDING_MODEL)`, **không truyền `dimensions`**; dim = `len(vector[0])` thực tế (expect 2048); `input_type` thử qua `extra_body` (`query` cho `embed_query`, `passage` cho ingest), retry không param khi 400; giữ OpenAI + st fallback sau. `provider="nvidia"` khi dùng NVIDIA.
4. **Config**: `config.py` thêm `NVIDIA_API_KEYS/CHAT_MODEL/EMBEDDING_MODEL/BASE_URL`; `sources.yaml` → `nvidia/nemotron-3-embed-1b`/2048; `vector_store.DEFAULT_DIM` → 2048 (default only).
5. **Eval**: `run_benchmark.py`, `run_rag_eval.py`, `run_ragas_eval.py`: default model → `os.getenv("NVIDIA_CHAT_MODEL",...)` **+ wiring client**: nếu model startswith `nvidia/` dùng `NVIDIA_BASE_URL` + key từ pool (giữ tương thích OpenAI cũ). Không chạy full benchmark.
6. **Secrets**: `.env.example`, `docker-compose.yml/dev`, `ci.yml`: thêm `NVIDIA_API_KEY/2/3`, `NVIDIA_CHAT_MODEL`, `NVIDIA_EMBEDDING_MODEL`, `NVIDIA_BASE_URL`.
7. **Tests**: mới `test_nvidia_key_pool.py` (round-robin, cooldown-skip, thread-safety smoke) + mock `test_llm_provider`/`test_embedder` (per-invoke rotation, fallback). Giữ suite xanh.
8. **Migrate thật** (sau tests xanh, local `data/qdrant_local_v117`): gọi `run_full_refresh` với **week suffix riêng** (vd `"<week>_nvidia2048"` hoặc param `collection_suffix` ~3 dòng trong `pipeline.py`) → collection mới 2048 → upsert → `swap_alias` → verify `alias_target` + `collection_info` + `search_knowledge` 1 query; collection cũ 1536 giữ cho `cleanup_old_backups(7)`. Smoke thêm 3 đường chat (`invoke`, `structured`, `bind_tools`). Ghi docs/chunks/dim vào WORKFLOW_STATE. Không benchmark full.

## Files To Change (đã chốt sau debate)
- Mới: `src/infrastructure/llm/nvidia_key_pool.py`, `src/tests/unit/infrastructure/llm/test_nvidia_key_pool.py`.
- Sửa: `src/infrastructure/llm/llm_provider.py` (NVIDIARotatingChat per-invoke, max_tokens=4096, max_retries=0), `src/infrastructure/rag/embedder.py` (dim từ vector thực tế, extra_body input_type graceful), `src/shared/config.py`, `src/infrastructure/rag/config/sources.yaml` (2048), `src/infrastructure/rag/vector_store.py` (DEFAULT_DIM 2048), `src/infrastructure/rag/pipeline.py` (~3 dòng param collection_suffix/week-override HOẶC gọi week suffix, tránh recreate xóa collection cũ), `evals/run_benchmark.py`, `evals/run_rag_eval.py`, `evals/run_ragas_eval.py` (default + client wiring), `.env.example`, `docker-compose.yml`, `docker-compose.dev.yml`, `.github/workflows/ci.yml`, `README.md` (note ngắn).
- Không sửa: `evals/baselines/baseline-v1.json`, reports benchmark, collection cũ 1536.
- Chạy thật: Qdrant local `data/qdrant_local_v117` (không động cloud).

## Current Status
- Debate DONE 14/10/2026 (REVISE accepted). **IMPLEMENT DONE 14/10/2026** — toàn bộ 8 bước plan, không benchmark full.
- **Files To Change (thực tế):** mới `src/infrastructure/llm/nvidia_key_pool.py` (~90 dòng), `src/tests/unit/infrastructure/llm/test_nvidia_key_pool.py` (9 tests); sửa `llm_provider.py` (NVIDIARotatingChat per-invoke, temperature=0/max_tokens=4096/max_retries=0, giữ OpenAI legacy khi thiếu NVIDIA keys), `rag/embedder.py` (primary NVIDIA, dim từ vector thật, extra_body input_type graceful, OpenAI-legacy dùng OPENAI_EMBEDDING_MODEL), `shared/config.py` (NVIDIA_*), `rag/config/sources.yaml` (2048), `rag/vector_store.py` (DEFAULT_DIM 2048), `rag/pipeline.py` (param collection_suffix + dim=len(vectors[0])), 3 eval scripts (default NVIDIA_CHAT_MODEL + client wiring nvidia/), `.env.example`, `docker-compose.yml/dev`, `ci.yml`, `README.md` (note ngắn). Không thêm dep.
- **Số migrate thật** (local `data/qdrant_local_v117`): collection mới `finsight_knowledge_2026w42_nvidia2048` — **33 docs / 237 chunks / dim 2048 / provider nvidia / status success** (manifest `vector_ok=True`); alias `finsight_knowledge` đã swap sang collection mới; collection cũ `..._2026w41` (236 pts) còn nguyên backup cho `cleanup_old_backups(7)`.
- **Verify live:** chat invoke OK (NVIDIA) + rotation thật (1 key 503 → cooldown → key kế tiếp thành công trong cùng request); embed smoke dim 2048 + `embed_query` (input_type=query) 2048; `search_knowledge` 1 query → 3 hits, top tt_96_2020 score ~0.51, không dim-mismatch; tool-chain (`bind_tools`+invoke) OK; structured `json_schema` OK với prompt registry thật (reformulator), `json_mode` bám schema kém (model, không phải code — xem note).
- **Tests:** full unit suite **746 passed / 0 failed** (baseline 737 + 9 mới).
- **Implementation Notes:** (1) Bug tự phát hiện & fix: `pool or get_pool()` — empty pool falsy do `__len__` → dùng `is not None`. (2) Không dùng `asyncio.Lock` (critical section không await). (3) `with_structured_output(fallback=False)` mặc định trả Groq trước (pre-existing, giữ nguyên semantics). (4) GROQ key trong `.env` vẫn 401 — fallback Groq chết nhưng chain vẫn đúng thứ tự (NVIDIA trước).
- **Caveat cho reviewer:** nemotron `json_mode` hay đặt sai tên key schema (`questions`/`standalone_question` thay vì `queries`/`rewritten`); production callers (reformulator/splitter) dùng `json_schema` đã verify OK; sentiment LLM path (non-default) dùng `json_mode` chưa verify live.

## Clarified Scope 2 (14/10/2026 — README curriculum, user chốt)
- Giữ nguyên số liệu thị trường có citation (11–13tr TK, FinLit 24%, Sun Life/TVS, Simplize 499k, tailwind AI 75%) + định vị Hướng C (giáo dục có trích dẫn, không khuyến nghị mua/bán).
- Thêm subsection mới giới thiệu 8 modules, mỗi module 1–2 dòng khái quát (lấy từ user + titles trong curriculum JSON M1–M8), kèm disclaimer "chỉ giáo dục, không khuyến nghị sản phẩm cụ thể (TT 135/2025)" + scope_note (số thuế/lãi suất tra nguồn hiện hành) + link tới `data/lessons/curriculum_tai_chinh_ca_nhan.json`. Không đưa giờ học/outcomes/learning paths chi tiết.
- Xóa subsection 6 (bảng chín muồi 5 tiêu chí + dòng kết luận). Giữ `Nguồn tham khảo — Pain Point` cuối README.
- Xong thì **push các thay đổi gần đây (NVIDIA batch + README) lên main** — user yêu cầu tường minh.

## Constraints 2
- Chỉ sửa `README.md` cho nội dung; không động code. Giữ mọi citation/link hiện có còn đúng.
- Push chỉ sau khi diff đã review (đúng files, không commit secrets — `.env` không track).

## Acceptance Criteria 2
1. README còn số liệu + định vị Hướng C, có 8 modules 1–2 dòng, có disclaimer + link curriculum JSON, không còn bảng chín muồi, còn nguồn tham khảo.
2. Markdown render OK, link relative tới `data/lessons/` đúng.
3. Push main thành công, báo commit hash + danh sách files đã push.

## Plan 2 (candidate — task nhỏ, 1 file)
1. Implementor sửa duy nhất `README.md` (dòng 18–66): giữ intro + stats (1–4, có thể gọn câu chữ nhưng giữ số + citation) + định vị (5) + thêm subsection `Nội dung giáo dục: 8 modules` (8 bullets 1–2 dòng + disclaimer + link) → xóa subsection 6 + kết luận.
2. Verify: đọc lại section, check link relative, grep không còn sót bảng.
3. Git: `git status` + `git diff --stat` + `git log --oneline -5` review → stage đúng files (README + batch NVIDIA đang pending) → commit message theo repo style → `git push origin main` → báo hash + URL. Không force-push, không amend commit fail.

## Files To Change 2
- Sửa: `README.md` (section 18–66 + giữ dòng 537).
- Không sửa: mọi file khác (ngoài batch NVIDIA đã làm trước đó, chỉ push kèm).
- Push: main (user yêu cầu tường minh).

## Current Status 2
- Debate DONE 14/10/2026 — APPROVE, không đổi plan. Lưu ý duy nhất: stage có chọn lọc sau khi review `git status` (không `add -A`, tránh lọt qdrant data/traces/`.env`). Plan 2 Approved, sẵn sàng implement + push.
- **IMPLEMENT + PUSH DONE 14/10/2026** — sửa duy nhất `README.md` section 18–67: giữ intro + stats mục 1–4 (11–13tr TK, FinLit 24%, Sun Life/TVS, Simplize 499k, tailwind AI 75%) + định vị Hướng C mục 5 kèm cam kết giáo dục; thêm subsection `Nội dung giáo dục: 8 modules` (8 bullets M1–M8 1–2 dòng, titles khớp curriculum JSON) + disclaimer giáo dục/TT 135/2025/scope_note + link relative `data/lessons/curriculum_tai_chinh_ca_nhan.json`; xóa subsection 6 (bảng chín muồi + kết luận). Giữ `Nguồn tham khảo — Pain Point` cuối file. Verify: grep "chín muồi" chỉ còn sót trong WORKFLOW_STATE.md (README sạch).
- **Push main OK:** commit `18ba5f9` `feat(llm,rag): nvidia key rotation + embedding 2048, readme curriculum` — 16 files (README + batch NVIDIA: nvidia_key_pool.py + test mới, llm_provider/embedder/config/sources.yaml/vector_store/pipeline, run_benchmark/run_rag_eval/run_ragas_eval, .env.example, docker-compose.yml/dev, ci.yml). `39001f5..18ba5f9 main -> main`, không force/amend. Không commit secret (scan cached diff sạch), không lọt qdrant/traces/`.env`/frontend.dev.log.
- **Caveat:** `data/lessons/curriculum_tai_chinh_ca_nhan.json` đang bị `.gitignore:39 data/` ignore → link README đúng locally nhưng file chưa lên remote; muốn hiện trên GitHub cần thêm exception `.gitignore` (ngoài scope Plan 2, để user quyết).

## Clarified Scope 3 (14/10/2026 — curriculum gaps, user chốt)
- Tools: làm cả 4 — `calculate_loan_schedule` (amortization + snowball vs avalanche), `calculate_future_value` (lãi kép, giá trị thực sau lạm phát, chi phí hưu 3 kịch bản), `calculate_pit` (TNCN theo quy định hiện hành, `verify_before_publish`), `budget_template` (50/30/20 + zero-based, reuse `generate_chart_spec` nếu rẻ). Dạng `@mcp.tool` như tools hiện có.
- RAG: implementor tự tìm nguồn chính thống (vbpl/thuvienphapluat, SBV, CIC, NHNN/Cục ATTT). Lãi suất theo spec user: Layer 1 điều hành + liên ngân hàng (SBV, khi đổi/hàng ngày), Layer 2 huy động niêm yết theo NH/kỳ hạn (hàng ngày, qua web NH hoặc Simplize/CafeF/Banker.vn), Layer 3 bình quân hệ thống + cho vay bq (SBV, hàng tháng).
- Thứ tự: tools tính toán trước, RAG sau. `calculate_pit` verify công thức trực tiếp từ văn bản chính thống ngay khi làm tools (không đợi RAG).
- Eval vẫn hoãn (như batch NVIDIA). Scope "không đầu tư/khuyến nghị sản phẩm" + disclaimer giữ nguyên.
- 13 tools stock giữ nguyên không đụng. Tools mới tách namespace riêng + agent mode `tutor` (theo curriculum: tutor chỉ expose education tools + `search_knowledge`; default `full` giữ hành vi cũ).
- Giả định chờ confirm (không block plan): Layer 2 daily là structured feed + tool đọc (kiểu `market_store`), không nhét snapshot hàng ngày vào embedding — Phase B làm sources tĩnh/SBV qua pipeline trước, daily-feed là follow-up nếu spike thấy nặng. Debater review điểm này.

## Constraints 3
- Pure calc tách khỏi MCP wrapper (test được offline, số đối chiếu tay). Mọi con số thuế/lãi suất ghi rõ nguồn + ngày hiệu lực trong docstring.
- Không sửa 13 tools stock; tutor filter default-off (không đổi hành vi mặc định).
- RAG migrate theo pattern đã chốt: collection tên riêng + swap alias + giữ backup (không `recreate` đè).
- Hoãn benchmark full; chỉ unit + live smoke. Planner không sửa code ngoài WORKFLOW_STATE.md.

## Acceptance Criteria 3
A1. 4 tools gọi được qua MCP + agent; unit tests với số tính tay (snowball/avalanche totals, FV công thức, PIT theo bậc đã cite, budget cộng đủ 100%).
A2. `AGENT_MODE=tutor` chỉ expose education + `search_knowledge` + `generate_chart_spec` (reuse pie/donut ngân sách); default `full` không đổi; 13 tools cũ untouched.
A3. **Sources tĩnh** ingest thành công (TNCN + hướng dẫn, KDBH/BHXH-BHYT, tín dụng/CIC, lừa đảo, SBV static rates) — ghi docs/chunks; alias swap an toàn; `search_knowledge` trả hits cho query thuế/bảo hiểm/lừa đảo. **Layer-2 daily listed-rate là follow-up, không thuộc acceptance batch này.**
A4. Scope/disclaimer (tutor prompt addendum) có mặt; output PIT luôn kèm nguồn + ngày hiệu lực + câu đối chiếu văn bản hiện hành; không benchmark full.

## Plan 3 (Approved sau debate 14/10/2026 — REVISE minor đã tiếp thu: 1-file giữ nguyên, tutor filter sau-load gồm chart_spec, Layer-2 tách follow-up, PIT guardrail)
**Phase A — 4 calc tools (1 file pure + 1 file MCP + tests):**
A1. Mới `src/application/services/education/calculators.py` (pure, không I/O): loan amortization + snowball/avalanche compare; FV nominal/real + retirement monthly (3 infl scenarios); PIT (brackets/thresholds là hằng số có cite + ngày hiệu lực, dễ update); budget 50/30/20 + zero-based validate.
A2. Mới `src/mcp_server/tools/education.py` (4 `@mcp.tool`, gộp 1 file thay vì 4 file theo pattern cũ — ít file hơn; tái dùng `call_service` helper) + đăng ký trong `tools/__init__.py`.
A3. Tutor mode: `config.py` thêm `AGENT_MODE` (default `full`); `agent.py` lọc allowlist (4 education + knowledge + `generate_chart_spec`) **ngay sau load, trước ToolNode + LLM-binding** + system prompt addendum từ curriculum. Ghi rõ tutor là UX-mode, không phải security boundary.
A4. Tests mới `test_education_calculators.py` (số tính tay, PIT pin từng bậc theo cite) + wiring mock (cả 2 mode); suite xanh. Smoke live 1 call/tool.
**Phase B — RAG sources tĩnh (sau A xanh):**
B1. Spike fetch từng nguồn (completeness title/text/url/date) → thêm vào `sources.yaml` (priority: TNCN ~2, tín dụng/CIC ~3, bảo hiểm ~3-4, lừa đảo ~4, SBV static ~4; parser hiện có, thêm mới chỉ nếu spike fail).
B2. Ingest qua `run_full_refresh` + collection riêng + swap alias (pattern NVIDIA batch). **Layer-2 daily listed-rate TÁCH follow-up** (structured store + tool đọc kiểu `market_store`, spike riêng) — batch này chỉ SBV static pages.
B3. Verify `search_knowledge` 1 query/nhóm nguồn mới; ghi docs/chunks vào WORKFLOW_STATE. Không benchmark.

## Files To Change 3 (dự kiến)
- Mới: `src/application/services/education/calculators.py`, `src/mcp_server/tools/education.py`, `src/tests/unit/.../test_education_calculators.py` (+ wiring test).
- Sửa: `src/mcp_server/tools/__init__.py`, `src/application/agents/agent.py` (tutor filter tối thiểu), `src/shared/config.py` (`AGENT_MODE`), `src/infrastructure/rag/config/sources.yaml` (+connectors nếu cần parser mới), `README.md` (note ngắn), `.env.example` (`AGENT_MODE`) nếu cần.
- Không sửa: 13 tool files stock, eval reports, benchmark harness.
- Chạy thật: ingest RAG local (pattern batch trước).

## Files To Change 3 (thực tế)
- Mới: `src/application/services/education/{__init__,calculators}.py`, `src/mcp_server/tools/education.py`, `src/tests/unit/application/services/education/{__init__,test_education_calculators}.py` (16 tests), `src/tests/unit/mcp_server/test_education_tools.py` (7 tests).
- Sửa: `tools/__init__.py` (+1 import), `shared/config.py` (`AGENT_MODE` default `full`), `application/agents/agent.py` (`TUTOR_TOOL_ALLOWLIST` + `_apply_agent_mode_filter` sau load/trước ToolNode-binding + `TUTOR_ADDENDUM` trong `_build_messages`), `rag/ingestion/connectors.py` (markers WAF `Request Rejected` + seed-thay-rác khi text<200 + 6 SEED_TEXTS), `rag/config/sources.yaml` (6 nguồn mới), `rag/cli.py` (`--suffix`), `mcp_server` test count 14→18, `.env.example` (`AGENT_MODE`), `README.md` (4 rows tools + note tutor/RAG).
- Không sửa: 13 tool files stock, eval reports/benchmark harness. Không benchmark (đúng scope).

## Current Status 3
- Debate DONE 14/10/2026 (REVISE minor accepted: A3 sửa scope tĩnh, allowlist +chart_spec, PIT guardrail, Layer-2 follow-up). Plan 3 Approved, sẵn sàng implement Phase A → B.
- **PHASE A DONE 14/10/2026** — full unit suite **769 passed / 0 failed** (baseline 746 + 23 mới: 16 calculators + 7 wiring), smoke live 4/4 tools.
  - A1 `calculators.py` pure: amortize + snowball/avalanche compare; FV nominal/real + retirement 3 kịch bản; PIT hằng số cite Luật 109/2025 Đ9 + NQ 110/NĐ 253 (giảm trừ 15.5M/6.2M, hiệu lực kỳ 2026); budget 50/30/20 + zero-based validate.
  - PIT verify: Reeracoen case 30M/1 NPT 2026 = 257,500 khớp code; bậc biên 10M→500k; 100M→20.5M; FV 100M/8%/5y nominal 146,932,808 real@4% 120,768,058; loan 100M/12%/12th payment 8,884,879.
  - A2 `education.py`: 4 `@mcp.tool` mỏng qua `call_service`; PIT output kèm source + effective_date + verify_note.
  - A3 tutor: `AGENT_MODE` default `full`; filter allowlist (4 edu + knowledge + chart_spec) sau load, trước ToolNode/binding; addendum trong `_build_messages`; comment UX-mode-not-security-boundary.
  - A4 tests số tay + cả 2 mode; 4 test failures giữa chừng đều là lỗi số tay trong test (real-FV, avalanche-order, case-sens), đã sửa test — không phải bug code.
  - Implementation Notes: (1) avalanche payoff_order[0] không phản ánh target khi minimums tự clear nợ nhỏ trước — assert bằng interest. (2) Không sửa 13 stock tools.
- **PHASE B DONE 14/10/2026** — ingest success local `data/qdrant_local_v117`: collection `finsight_knowledge_2026w42_edu` — **48 docs / 877 chunks / dim 2048 / provider nvidia**; alias đã swap; backup giữ (`..._2026w42_nvidia2048` 237 pts + `..._2026w41`; cleanup xóa 0).
  - B1 spike verdict: TNCN/KDBH/BHXH/SBV-static qua luatvietnam fetch OK (626KB/2MB/225KB/230KB) → `generic_html`, không parser mới; CIC DNS/403 fail + SBV WAF-block + vbpl deep-URL trả homepage-shell + thuvienphapluat 403 → dùng seed đã verify (nhóm nợ TT 11/2021 + TT 31/2024; SBV 4.5/3.0/5.0 QĐ 1123 HL 19/06/2023); scam crawl tinnhiemmang.vn được 10 pages + seed fallback.
  - Priorities: pit_law_109=2, cic/kdbh/bhxh=3, scam/sbv=4.
  - B3 verify `search_knowledge` 5 queries → top đúng nguồn: PIT pit_law_109 0.508; CIC cic_debt_groups 0.51; scam 0.349; SBV sbv_policy_rates 0.523; BHXH bhxh_2026_rates 0.44. Không dim-mismatch.
  - Follow-up (ngoài batch): Layer-2 daily listed-rate (structured store + tool đọc kiểu market_store).

## Request mới (14/10/2026 — rates SQL store, Layer-2 follow-up)
- User đưa spec chi tiết: 6 nhóm lưu SQL (huy động niêm yết snapshot daily giữ 6–12th; cho vay niêm yết weekly/khi đổi; bình quân SBV monthly giữ vĩnh viễn; điều hành SBV giữ vĩnh viễn + effective_date; VNIBOR daily giữ 3–6th; metadata NH lâu dài) + không lưu HTML thô/intermediate/thỏa thuận + cache strategy (SQL-first, crawl khi stale >12–24h huy động />1th SBV / force_refresh / hash đổi) + trường `crawled_at` + `source`.
- Đối chiếu repo (14/10/2026): đã có pattern mirror sẵn — `src/infrastructure/market_store/` (`store.py` sqlite, `ingest.py`, `scheduler.py` opt-in `ENABLE_MARKET_SCHEDULER`, `cached_adapter.py` read-through) + RAG scheduler CN 02:00. Rates store nên mirror pattern này thay vì thiết kế mới.

## Open Questions (chờ user chốt)
- (sẽ hỏi trong chat)

## Constraints (bổ sung)
- Planner: không sửa code ngoài WORKFLOW_STATE.md.

## Request mới (15/10/2026 — video M3L2 9:16, execution trực tiếp theo lệnh user)
- Chạy pipeline `data/xu-video`: `pip install edge-tts` → `python scripts/tts.py M3L2` → `node scripts/render.mjs M3L2 --force` (workdir `data/xu-video`, vì `scripts/` nằm ở đó chứ không phải repo root).
- Khảo sát 15/10: node 24 + npm 11 + py 3.13 OK; thiếu node_modules, edge-tts, ffmpeg/ffprobe; Chrome có sẵn (ProgramFiles) + ms-playwright cache; `public/lessons/M3L2_scenes.json` đủ; audio mới có S1.mp3; M3L2 còn placeholder [[TÍNH BẰNG CÔNG CỤ]] → --force = bản draft (user đã chốt).
- Plan: cài thiếu (npm i, pip edge-tts, ffmpeg qua winget) → TTS → render với CHROME trỏ Chrome sẵn có → verify out/M3L2.mp4.

## Request mới (15/10/2026 — poses Trâu Tí + move code sang frontend/)
- User thêm assets poses trong `data/trau-video/assets/trau/` (vui/nghĩ/chỉ/vẫy). Cần đối chiếu kịch bản xem thiếu pose nào + chuyển code khỏi `data/` sang `frontend/`.
- Đối chiếu 15/10: 31 lesson JSONs dùng 5 poses — celebrate, idle, point, think, wave (shrug không bài nào dùng). Vector `Trau.tsx` vẽ đủ cả 5 (celebrate→happy alias). SVG assets đủ 5 (+sheet). PNG assets thiếu đúng 1 file: `trau_idle.png`. `TrauSheet` chỉ show 4 poses (thiếu idle).
- Lưu ý: `data/xu-video/` đã bị thay bằng `data/trau-video/` (project viết lại: TrauSvg vector + TrauStill + export-mascot.mjs); node_modules/audio/out chưa có ở trau-video (làm lại khi cần render). Hai cây JSON `video_scenes/` ≡ `public/lessons/` (M3L2 diff sạch), rename Trâu Tí đã áp cả hai (0 sót).
- Move: `frontend/` là Next 16 + React 19 + src/{app,components,...}; Remotion app là React 18 + package.json riêng → không merge package, chỉ đặt subfolder standalone được.
- Lịch sử: video M3L2 draft đã render OK từ `data/xu-video/out/M3L2.mp4` (1080x1920, 118.8s) trước khi thư mục bị thay bằng trau-video; setup máy (edge-tts, FFmpeg, Chrome) vẫn còn, chỉ mất node_modules/audio/out theo folder cũ.

## Clarified Scope 4 (15/10/2026 — poses + move frontend, user chốt)
- Gen `trau_idle.png` (trong suốt, via `remotion still`) trong batch này; tiện thêm idle vào `TrauSheet` cho đồng bộ.
- Move cả project Remotion `data/trau-video/` → `frontend/trau-video/` (standalone package, giữ package.json React 18 riêng — không merge vào Next).
- Scenes gộp một nơi: giữ `public/lessons/` (bản pipeline đọc), xóa `data/video_scenes/` (đã diff đồng bộ).
- Xóa `data/trau-video/` + `data/video_scenes/` sau khi verify move. Code sang frontend/ = vào git (data/ đang ignore).

## Constraints 4
- Không đụng Next app (không merge deps React 18/19; kiểm tra tsconfig `include` + Dockerfile context không quét nhầm `trau-video/node_modules`).
- Kiểm tra `frontend/.gitignore` có chặn mp3/mp4/audio/out không trước khi commit; render fixes Windows (npx.cmd + quote CHROME) còn hiệu lực ở chỗ mới thì giữ.
- Xóa data/ cũ chỉ sau khi diff -r sạch + pipeline chạy được ở chỗ mới. Planner không sửa code ngoài WORKFLOW_STATE.md.

## Acceptance Criteria 4
1. `frontend/trau-video/` đủ project (src/scripts/public/package.json...), `public/lessons/` 31 JSONs + index, `assets/trau/trau_idle.png` tồn tại nền trong suốt.
2. `remotion still` idle chạy OK ở chỗ mới (= pipeline sống sau move).
3. `data/trau-video/` + `data/video_scenes/` đã xóa; grep repo không còn reference chết (video_scenes/xu-video/data/trau-video).
4. `git status` chỉ hiện files định commit (node_modules/out/audio-build? theo .gitignore).

## Plan 4 (Approved sau debate 15/10 — REVISE đã tiếp thu)
1. Đọc: `frontend/tsconfig.json`, `eslint.config.mjs`, `frontend/.gitignore`, `frontend/.dockerignore` (nếu thiếu thì tạo), `frontend/Dockerfile`, `trau-video/package.json` name, `scripts/render.mjs`, `src/Root.tsx` (composition `TrauPose`).
2. Fix bắt buộc TRƯỚC move: tsconfig `exclude` += `trau-video` (+out/node_modules) + eslint ignore tương ứng; `.gitignore` += `trau-video/node_modules/`, `trau-video/out/` (giữ assets PNG được track); `.dockerignore` tương tự (Dockerfile `COPY . .`).
3. Move copy-verify-delete: copy `data/trau-video/` → `frontend/trau-video/`; verify đủ 31 JSON + index ở `public/lessons/` + `diff -r` sạch mới xóa `data/trau-video/` + `data/video_scenes/`.
4. Khôi phục fix Windows trong `scripts/render.mjs` ở chỗ mới (npx.cmd + shell + quote CHROME).
5. `npm install` (+compositor-win32 nếu sót) → `remotion still <TrauPose> --props '{"pose":"idle"}'` → `assets/trau/trau_idle.png` → verify alpha (PIL RGBA + góc trong suốt) → thêm idle vào `TrauSheet`.
6. Cập nhật references paths cũ + WORKFLOW_STATE. Báo `git status` (chưa commit/push).
1. Grep references repo-wide (video_scenes, xu-video, data/trau-video) + đọc `frontend/.gitignore`, `frontend/tsconfig.json` include, `frontend/Dockerfile`, `trau-video/package.json` name, `render.mjs` (còn fix Windows không), `Root.tsx` (composition IDs cho still).
2. Move filesystem `data/trau-video/` → `frontend/trau-video/`; gộp scenes (public/lessons đã đủ — verify đủ 31 + index rồi mới xóa video_scenes).
3. `npm install` ở chỗ mới (+ compositor-win32 nếu npm bỏ sót) → export SVG idle (đã có, skip nếu còn) → `remotion still` pose idle → `assets/trau/trau_idle.png` → verify alpha (PIL mode RGBA + corners transparent) → thêm idle vào `TrauSheet`.
4. Cập nhật references (README/docs nào trỏ paths cũ) + WORKFLOW_STATE paths.
5. Xóa `data/trau-video/` + `data/video_scenes/` (sau diff -r + still OK). Báo `git status` (chưa commit/push — user chưa yêu cầu).

## Files To Change 4 (dự kiến)
- Move: `data/trau-video/` → `frontend/trau-video/` (nguyên cây).
- Mới: `frontend/trau-video/assets/trau/trau_idle.png`.
- Sửa (nhỏ): `src/TrauStill.tsx` (+idle), `package.json` name nếu còn xu-video, docs/refs paths, `frontend/.gitignore` nếu chặn media cần track.
- Xóa: `data/trau-video/`, `data/video_scenes/`.

## Current Status 4
- Debate DONE 15/10/2026 (REVISE accepted: tsconfig/eslint exclude, gitignore/dockerignore nested, khôi phục fix Windows, still tường minh + verify alpha, copy-verify-delete). Plan 4 Approved, sẵn sàng implement.
- **IMPLEMENT DONE 15/10/2026** — đủ 7 bước, không block.
  - Fix bắt buộc TRƯỚC move: `frontend/tsconfig.json` exclude += `trau-video`; `frontend/eslint.config.mjs` globalIgnores += `trau-video/**`; `frontend/.gitignore` += `trau-video/node_modules/`, `trau-video/out/` (PNG assets vẫn track được — không có rule chặn media); mới `frontend/.dockerignore` (2 dòng tương tự; file trước đó chưa tồn tại, frontend build context = `./frontend` nên root `.dockerignore` không áp dụng).
  - Move copy-verify-delete: copy `data/trau-video/` → `frontend/trau-video/`, `diff` cây file IDENTICAL; verify `public/lessons/` = 30 lessons + index, `diff` content với `data/video_scenes/` sạch → đã xóa `data/trau-video/` + `data/video_scenes/`.
  - Windows fix khôi phục ở `frontend/trau-video/scripts/render.mjs` (npx.cmd + shell:true trên win32 + quote `--browser-executable="<CHROME>"` vì path có dấu cách).
  - `npm install` OK (`@remotion/compositor-win32-x64-msvc` có sẵn, không cần cài thêm) → `remotion still TrauPose --props '{"pose":"idle"}'` → `assets/trau/trau_idle.png` (1040x820, RGBA, 4 góc alpha=0 → TRANSPARENT_OK) → thêm `idle` vào `TrauSheet` (giờ 5 poses; `idle` hợp lệ trong `TrauPose` type) + `tsc --noEmit` sạch.
  - Grep repo-wide `video_scenes|xu-video|data/trau-video`: chỉ còn sót trong WORKFLOW_STATE.md (lịch sử, giữ nguyên) — không còn reference chết ở docs/code sống; `trau-video/README.md` dùng relative paths nên đúng ở chỗ mới.
  - `git status`: `frontend/trau-video/` hiện untracked (sẵn sàng commit sau); node_modules/out trong đó đã ignore đúng; `data/` deletions không hiện vì `data/` đang gitignore. KHÔNG commit/push (user chưa yêu cầu).
  - Note: `frontend/frontend.dev.log` untracked có sẵn (rác pre-existing, không động).
- **PUSH DONE 15/10/2026:** commit `488269e` `feat(video): move trau-video to frontend + idle pose` — 63 files (frontend/trau-video/ nguyên cây: src/scripts/public-lessons-30+index/assets-5-poses+sheet/package.json+lock/remotion.config/tsconfig/README; + tsconfig.json exclude, eslint.config.mjs ignore, .gitignore 2 dòng, .dockerignore mới 2 dòng). `18ba5f9..488269e main -> main`, không force/amend. Review trước push: staged đúng 5 paths Plan 4 (không `add -A`), cached diff sạch secret (không `.env`/DB/log/mp3/mp4/out/node_modules; PNG assets được track theo scope). Unstaged còn lại để nguyên, không động.

## Request mới (15/10/2026 — mascot động + lip-sync theo giọng đọc)
- User muốn Trâu Tí chuyển động sống động, lip-sync theo VO (gợi ý WebM nền trong suốt hoặc Lottie).
- Khảo sát 15/10: render hiện dùng `TrauSvg` vector + miệng vẽ theo pose; audio VO là mp3 per-scene (`public/audio/<ID>/Sx.mp3`, hiện chưa có ở trau-video — render nào cũng phải TTS lại).
- Library verification (websearch 15/10, remotion.dev docs): `@remotion/media-utils` có `useAudioData` + `visualizeAudio` (+ `getWaveformPortion` cho volume đơn giản) — fake lip-sync theo biên độ ngay trong render, không cần preprocess audio. Cần cài thêm package (`@remotion/media-utils` chưa có trong trau-video deps).
- Đánh giá sơ bộ: Lottie cần file animation authored (không có, AI gen không đáng tin) → loại; WebM alpha cần nguồn video alpha (stack hiện không gen được) → loại; hướng khả thi: SVG procedural + miệng driven bởi audio (biên độ), cộng word-boundary timing từ edge-tts nếu cần mím môi theo từ.

## Clarified Scope 5 (15/10/2026 — lip-sync Trâu Tí, user chốt)
- Fake lip-sync theo biên độ (không phoneme): miệng há/mím theo tiếng nói thật của từng scene.
- Phạm vi chuyển động: miệng + đầu gật + tay/body nhún theo nhịp nói ( Better: head-group nod, arms-group swing, whole-body bounce — đều driven bởi energy đã smooth).
- Bài đầu tiên = M3L2 (pilot đang làm; cùng đường code nên đổi bài khác rẻ nếu user muốn).
- Kỹ thuật: `useAudioData` + `getWaveformPortion` (volume đơn giản, rẻ hơn full spectrum) từ `@remotion/media-utils` (chưa có trong deps → thêm 4.0.x). Audio dùng chính file mp3 VO per-scene (phải TTS lại M3L2 vì folder mới chưa có audio). Vẫn --force draft (placeholder số chưa điền).

## Constraints 5
- Không-audio compositions (TrauSheet/stills) vẫn chạy (fallback miệng pose khi audioData null).
- Mouth mới phải tôn trọng pose (happy cười hở sẵn → mở rộng thêm; think mím → hé khi nói).
- Không đụng Lesson/Root structure ngoài việc truyền audio path + frame offset (implementor đọc Lesson.tsx trước để nối đúng offset).
- Planner không sửa code ngoài WORKFLOW_STATE.md.

## Acceptance Criteria 5
1. M3L2 render có miệng đóng/mở theo tiếng (frames kiểm chứng: lúc nói há, lúc ngừng mím) + đầu gật + tay/body nhún.
2. TrauSheet/stills không-audio vẫn OK; `tsc` sạch.
3. Vẫn --force draft (placeholder chưa điền) — không nhận là final.

## Plan 5 (Approved sau debate 15/10 — REVISE đã tiếp thu)
1. Deps: thêm `@remotion/media-utils@4.0.x` + npm install.
2. `SceneView.tsx`: hook `useAudioData(staticFile(audio scene))` vô điều kiện + `getWaveformPortion(frame local — Series.Sequence đã reset nên khớp Audio per-scene)` → EMA smooth → energy; null-safe (audioData null → energy 0, giữ nguyên như cũ).
3. `Trau.tsx`: MOUTH MORPH không overlay — tham số hóa miệng sẵn có theo `mouthOpen`: open≈0 giữ miệng pose; open>0 interpolate smile-line→há (idle/point/wave), scale miệng há sẵn (happy), hé mím (think).
4. `Mascot.tsx`: gật/nhún ở DOM-level — scale biên độ bob/tilt/pop hiện có theo energy (KHÔNG bọc `<g>` rotate trong SVG — pivot sai sẽ detach đầu/tay).
5. TTS lại M3L2 → render `--force` (CHROME) → verify frames nói/ngừng + `tsc` sạch → báo out/M3L2.mp4.

## Files To Change 5 (đã chốt sau debate)
- Sửa: `frontend/trau-video/package.json` (+@remotion/media-utils 4.0.x), `src/trau/Trau.tsx` (mouth morph theo open, KHÔNG overlay ellipse riêng), `src/Mascot.tsx` (scale bob/tilt theo energy, KHÔNG <g> rotate), `src/SceneView.tsx` (audio hook + EMA smooth + pass energy/mouthOpen).
- Không sửa: Lesson/Root structure, render.mjs, tts.py, scenes JSON.
- Gen: `public/audio/M3L2/*` (TTS lại), `out/M3L2.mp4` mới.

## Current Status 5
- Debate DONE 15/10/2026 (REVISE accepted). Plan 5 Approved, sẵn sàng implement.
- **IMPLEMENT DONE 15/10/2026** — đủ 5 bước, không cần escalate sang visualizeAudio.
  - Deps: `+@remotion/media-utils@4.0.250` (khớp remotion 4.0.250), npm install OK.
  - `src/SceneView.tsx`: `useAudioData(staticFile(audio scene))` vô điều kiện + `getWaveformPortion` frame local (Series.Sequence đã reset) → windowed-avg ≈ EMA (body 21-frame ~0.7s, mouth 3-frame) → energy/mouthOpen; null-safe (audioData null → 0, render như cũ).
  - `src/trau/Trau.tsx`: mouth MORPH qua prop `mouthOpen` (Trau + TrauSvg): open≈0 giữ miệng pose (opacity crossfade `talk=open*2.5`); open>0 interpolate smile-line→ellipse há (idle/point/wave + lưỡi khi open>0.5), happy scale control-point `14+22*open`, think hé mím `ry=2+7*open`. Không vẽ miệng thứ hai.
  - `src/Mascot.tsx`: nhận energy/mouthOpen; scale biên độ bob/tilt/pop sẵn có theo energy + bounce/tilt nhịp nói (`-|sin|*14e`, `sin*2e`); DOM-level transform, không `<g>` rotate.
  - **API correction (tsc bắt được):** `getWaveformPortion@4.0.250` nhận `startTimeInSeconds/durationInSeconds` (KHÔNG phải startFrame/durationInFrames) + trả `Bar[]{index,amplitude}` (KHÔNG phải number[]) — đã fix theo `.d.ts`, `tsc --noEmit` sạch.
  - Calibrate bằng astats thật trên S1.mp3: speech RMS -12..-30dB (≈amp 0.03–0.25), silence -90dB/-inf (≈0) → threshold 0.015, gain mouth ×8, energy ×6.
  - TTS M3L2: 9 scenes, VO 112.6s (S1 9.84 … S8 21.888). Render `--force`: `out/M3L2.mp4` 25MB, 3564 frames, 118.8s.
  - **Verify XEM HÌNH:** frame 5s (S1 speaking, idle) miệng HÁ tròn vs frame 10s (tail padding sau audio 9.84s) miệng MÍM smile-line — phân biệt rõ. TrauSheet still OK: 5 poses, miệng pose nguyên bản.
  - Vẫn --force draft (placeholder số chưa điền) — không nhận final. Không sửa Lesson/Root/render.mjs/tts.py/scenes JSON.

## Next Agent
- reviewer (review Plan 5: mouth morph + DOM bounce + TTS/render M3L2 + frames verify)

## Debate Notes (15/10/2026 — Plan 5 lip-sync)
- Đã đọc: Scope 5/Constraints 5/Acceptance 5/Plan 5/Files 5 + `SceneView.tsx` (frame local, Audio per-scene) + `Mascot.tsx` (pop/bob/tilt DOM-level) + `Trau.tsx` (head 49-87, mouth 71-74 per-pose, arms 89-99) + `Lesson.tsx` (Series.Sequence per scene, frame local) + `Root.tsx` (Lesson/TrauSheet/TrauPose) + `package.json` (remotion 4.0.250 → media-utils 4.0.x khớp).
- (1) Hook placement: SceneView ĐÚNG, không cần Lesson level — vì mỗi scene là Series.Sequence riêng, useCurrentFrame trong SceneView đã là local 0..f-1, Audio cũng start tại đầu sequence nên getWaveformPortion(startFrame=frame local) đã aligned. Lesson-level chỉ thêm plumbing offset tay, phức tạp vô ích.
- (2) Mouth vs pose: Plan overlay ellipse riêng sẽ vẽ 2 miệng (happy đã há #7A2E22; think mím; idle/point/wave smile-line) → xung đột visual. Phải morph miệng sẵn có theo open (happy scale miệng há; các pose khác interpolate smile-line → há), open≈0 giữ nguyên pose.
- (3) <g> head/arms: rotate SVG quanh origin (0,0) mặc định sẽ quăng đầu/tay lệch (pivot xa neck/shoulder ~0,72/±66,38) → phá layout. Translate nhỏ thì an toàn nhưng rotate cần pivot tường minh.
- (4) Đường đơn giản hơn: gật/nhún KHÔNG cần chạm Trau — Mascot đã có bob/tilt DOM-level, chỉ cần scale biên độ theo energy. Chỉ miệng mới bắt buộc sửa Trau. Whole-SVG-scale đơn thuần thì KHÔNG đạt Acceptance (không có miệng đóng/mở theo tiếng).
- Verdict REVISE: giữ bước 1+4+5, sửa bước 2+3 theo hướng trên + hook gọi vô điều kiện với null-safe fallback cho stills (không-audio).

## Debate Notes (14/10/2026 — NVIDIA migration)
- Đã đọc: Request/Clarified Scope/Library verification/Plan candidate/Files To Change + code thật `llm_provider.py` (LLMChain primary→Groq fallback, `_OPENAI_KNOWN_KWARGS` đã pass tools/tool_choice), `embedder.py` (OpenAI client sync, batch 100, không truyền dimensions — an toàn với embed-1b chỉ nhận 2048), `config.py` (chưa có NVIDIA_*), `vector_store.py` (DEFAULT_DIM 1536, `ensure_collection(dim)` runtime override được), `pipeline.py` (`run_full_refresh` lấy embed_model từ sources.yaml, `ensure_collection(recreate=True)` cùng tên week, dim lấy từ `embedder.dim`), `sources.yaml` (pin 1536).
- Library behavior (từ verification 14/10 + code): NVIDIA NIM OpenAI-compatible qua `ChatOpenAI(base_url)` + `OpenAI(base_url)` là đúng, không cần `langchain-nvidia` (đồng ý loại dep). Embed-1b dim native 2048, không truyền dimensions là an toàn nhất. `input_type` (query/passage) nếu có thì qua `extra_body`, phải graceful-fallback khi 400 (OpenAI SDK bản cũ không có param này).
- Điểm yếu plan cũ: (1) `run_full_refresh(force=True)` cùng week name + `recreate=True` sẽ XÓA collection 1536 trước khi ingest mới xong → mất backup + alias gián đoạn, trái với yêu cầu "giữ collection cũ". (2) Eval chỉ đổi default model string là chưa đủ — code eval vẫn dựng client với OPENAI key/base_url mặc định → vẫn gọi api.openai.com và fail. (3) Chat wrapper chưa chốt semantics xoay key cho `with_structured_output`/`bind_tools` (bind một lần, invoke nhiều lần → key bị chốt nếu pick ở bind-time) + chưa nêu `max_tokens` tường minh (NVIDIA dễ 500 nếu thiếu) + `max_retries` SDK phải =0/1 mỗi key nếu không SDK retry cùng key hỏng 3 lần che mất pool rotation.
- KeyPool không over-engineering: 1 file ~60 dòng (`get_next` + `report_success/failure` + cooldown dict + threading.Lock ngắn, không cần asyncio.Lock vì không await trong critical section) là mức tối giản chấp nhận được — không có helper sẵn để reuse. Dùng chung 1 pool cho chat+embed (đơn giản hơn 2 pool).
- Không tìm được plan đơn giản hơn đáng kể: giữ nguyên 8 bước, chỉ sửa 3 điểm trên + chốt dim từ vector thật thay vì infer chuỗi model.

## Request mới (15/10/2026 — học Langfuse trace UI MIT cho repo mình)
- User báo `rea-agents 6.5.0` cài global + `rea setup --client opencode` applied (MCP registration + skill reverse-engineer-anything vào opencode.jsonc, doctor healthy:true, skill aligned v42) và muốn dùng tool này để nghiên cứu cách các tính năng opensource MIT của Langfuse triển khai để học theo.
- User dẫn sẵn phát hiện: Langfuse trace UI (MIT) có TracesTable ~20 cột + visibility/sorting/search/row-selection; Detail tabs (Preview/Messages/Attributes/Scores/Log) + span tree collapse/select/hover-prefetch (virtualized) + timeline dense + graph DAG + metadata badges + human scores/feedback + comments per node + copy-IDs + delete + truncation notice; không dính `ee/` ở file đã kiểm tra.
- User nêu ràng buộc: spans nhà mình phẳng (retrieve/rerank/build_llm_input…), không parent-child như observations → cây thật cần đổi schema, không học trong một nốt nhạc.
- User đề xuất 8 mục theo giá trị/công sức: (1) waterfall duration bars, (2) tabs detail (Tổng quan/Chunks/Memory/RAGAS/Raw), (3) click span xem IO JSON expandable, (4) column visibility + sorting bảng list, (5) copy trace/span ID một chạm, (6) truncation notice + JSON viewer, (7) search trace ID + filter ngày, (8) human feedback tab (DB đã có bảng feedback, thiếu UI chấm tay cạnh RAGAS auto).
- Yêu cầu: kiểm tra kỹ lại chỗ thiếu sót rồi lên plan chi tiết — triển khai trước các phần KHÔNG đụng db migration, phần cần migration vẫn plan chi tiết nhưng để sau.

## Đối chiếu nhanh repo mình (15/10/2026 — planner khảo sát, chưa plan)
- Backend `src/interfaces/api/routes/traces.py`: list chỉ `limit/offset/status/min_duration_ms/name_filter` (max 200), luôn `ORDER BY started_at DESC`, không search trace_id, không filter ngày, không sorting param; detail `GET /{trace_id}` trả full `trace{spans}`.
- Store `tracing/storage.py`: bảng `traces(trace_id,root_name,status,started_at,ended_at,duration_ms,num_spans,total_tokens,llm/tool_count)` + `spans(span_id,trace_id,parent_span_id,name,kind,request_id,started_at,ended_at,duration_ms,status,model,provider,prompt_name/version,tokens,inputs/outputs/attributes/error)` — **đã có `parent_span_id` ở schema + tracer set qua context** (`tracer.py` start_span/begin_span), trái với nhận định "phẳng hoàn toàn" — cần verify dữ liệu thật (tỉ lệ parent null + tên spans) trước khi kết luận có dựng được tree không.
- Tracer truncate `max_content_chars=2000` (env `TRACE_MAX_CONTENT_CHARS`) + `safe_json` cắt kèm `...[truncated N chars]` — không phải "cắt 500 chars âm thầm"; frontend hiện không hiện notice.
- Frontend `traces/page.tsx`: grid Card list (limit=20 cứng, slice id 8-12 chars, badge status, root_name, duration, num_spans), không table/sort/visibility/search. `traces/[id]/page.tsx`: dump raw JSON trong `<pre>`, không tabs/tree/timeline/IO riêng/copy/truncation notice.
- Frontend deps: đã có `@radix-ui/react-tabs` (tabs rẻ), chưa có table lib; `components/ui` có Card/Badge (cần kiểm tra table/button/dialog có sẵn không khi plan).
- Feedback/RAGAS: grep repo không thấy bảng feedback nào (chỉ RAGAS eval scripts `run_ragas_eval.py` + `ragas>=0.2.6`); tuyên bố "DB đã có bảng feedback" chưa đối chiếu được — cần user chỉ file/migration cụ thể, nếu không thì feedback UI = cần migration (đi nhóm sau).
- rea doctor thực tế 15/10: `healthy:false` (thiếu engines hopper/ghidra/ida/jadx + drift 3 clients), chỉ `registration:opencode = aligned`, `skill v42 aligned`. Các engines thiếu là binary-RE, không liên quan task UI web này → dùng rea reverse-engineer-anything cho Langfuse TS/React là sai tool; nên dùng webfetch/docs-seeker + đọc trực tiếp GitHub langfuse (MIT web/src) thay vì rea.

## Open Questions (chờ user chốt — sẽ hỏi trong chat)
- DONE 15/10/2026 — user đồng ý toàn bộ 6 đề xuất (qua chat "Đồng ý... lên plan, debate rồi triển khai"): bỏ rea cho task này, cho query readonly traces.db, feedback chưa có = nhóm migration sau, batch 1 = 7 mục không-migration, chỉ học ý tưởng MIT + pin commit, chuyển sang Client Components + gate tsc/eslint/unit.

## Constraints (bổ sung)
- Planner: không sửa code ngoài WORKFLOW_STATE.md.

## Current Status
- Phase 1 Clarify DONE 15/10/2026: đã đọc WORKFLOW_STATE + đối chiếu traces backend/frontend/store/tracer + frontend deps + rea doctor; đã hỏi 6 câu, user đồng ý toàn bộ → sang Phase 2.

## Clarified Scope 6 (15/10/2026 — Langfuse trace UI, user chốt toàn bộ)
- Diễn đạt lại: nghiên cứu ý tưởng (không copy code) từ Langfuse trace UI opensource MIT để nâng cấp trang Traces nhà mình; chia 2 batch — Batch 1 (không đụng db migration, làm trước) 7 mục, Batch 2 (cần migration hoặc phức tạp, plan chi tiết nhưng để sau).
- Tool: KHÔNG dùng rea reverse-engineer-anything (sai domain binary-RE + doctor healthy:false thực tế); dùng webfetch + đọc trực tiếp GitHub langfuse `web/src` ở 1 commit pin, đối chiếu `MIT` vs `ee/`.
- Parent-child: schema đã có `parent_span_id`; được query readonly `data/traces/traces.db` để xác định tree thật vs phẳng thật; nếu phẳng thật thì waterfall "xếp theo started_at + indent theo kind" thay vì tree thật.
- Feedback: grep không thấy bảng feedback → xếp human-feedback UI vào Batch 2 (cần migration); Batch 1 không đụng DB schema traces/spans.
- Batch 1 = 7 mục: (1) waterfall duration bars, (2) tabs detail Tổng quan/Chunks/Memory/RAGAS/Raw, (3) click span xem IO JSON expandable, (4) column visibility + sorting bảng list, (5) copy trace/span ID một chạm, (6) truncation notice + JSON viewer, (7) search trace ID + filter ngày.
- Batch 2 = plan chi tiết để sau: human scores/feedback + comments per node + graph DAG view + virtualized hover-prefetch + row selection + delete dialog (+ scores/metadata badges nếu cần cột mới).
- Frontend: đồng ý chuyển traces list/detail sang Client Components + query params (từ Server Components hiện tại).

## Constraints 6
- Chỉ học ý tưởng, tự implement theo stack nhà mình (Next 16 + React 19 + Tailwind 4 + Radix tabs đã có, không thêm table lib nặng nếu native table đủ); không copy code Langfuse verbatim; ghi rõ nguồn ý tưởng trong code comment/docs.
- Không migration DB trong Batch 1: chỉ dùng cột hiện có (traces/spans như storage.py); mọi cột mới (scores, tags, session, userId, version, release, env, cost, comments) thuộc Batch 2.
- Không đổi semantics tracer/backend ghi (truncate 2000 chars giữ nguyên); chỉ cải thiện hiển thị + API read (thêm query params search/sort/filter).
- Admin-only giữ nguyên (cả list + detail đã gate admin); không mở public.
- Planner không sửa code ngoài WORKFLOW_STATE.md.

## Acceptance Criteria 6
- Batch 1 (nghiệm thu implementor): 7 mục chạy được trên data thật; `tsc --noEmit` sạch; `eslint` sạch; unit suite không regression (mở rộng `test_traces_api.py` cho query params mới); live smoke admin xem list + detail đúng.
- Batch 2: chỉ yêu cầu plan chi tiết (schema đề xuất + UI sketch + thứ tự), chưa implement.
- Không benchmark full; không đụng RAGAS/eval harness.

## Library verification 6 (15/10/2026 — planner verify trước plan)
- DB thật (readonly `data/traces/traces.db` 2.4MB): 489 traces / 3387 spans; `parent_span_id IS NULL`=489 (đúng 1 root/trace), NOT NULL=2898 → **tree thật dựng được, bác bỏ nhận định "phẳng"**. Mẫu `c8f875b7` 32 spans depth 3 tầng: `agent.run` (root) → `reason|llm_provider.chain|action|tool` (L1) → `ChatOpenAI|reason` (L2). Waterfall + collapsible tree làm được Batch 1, không migration. Trace mới nhất 1 span đơn (running/dang dở) là edge bình thường.
- Langfuse LICENSE (webfetch GitHub raw): MIT ngoài `ee/`, `web/src/ee/`, `worker/src/ee/` — khớp user báo; implementor pin 1 commit rồi chỉ đọc ngoài `ee/` (TracesTable/TraceTimelineDense/TraceTree ở `web/src` — path file đổi nhanh theo version nên không pin path cứng ở đây, chỉ pin commit lúc implement).
- Frontend sẵn: `components/ui/{table,tabs,button,badge,input}.tsx` đều có → Batch 1 không thêm dep (Radix tabs + shadcn table + native `<details>`/div bars đủ; không cần react-window/recharts cho waterfall).
- Tracer truncate 2000 chars (`TRACE_MAX_CONTENT_CHARS`) + suffix `...[truncated N chars]` — frontend chỉ cần detect suffix để hiện Badge notice (không un-truncate được vì bản full không lưu).
- Backend test pattern `test_traces_api.py` 6 tests rõ ràng → mở rộng cho query params mới rẻ.

## Plan 6 (Approved sau debate 15/10 — REVISE 7 điểm đã tiếp thu, xem Debate Notes 6)
- Using brainstorming to classify: this looks **bounded** (flow traces list/detail đã có) nên present short design qua Plan này thay vì full spec doc.
1. **Backend read-only API** (`routes/traces.py` + `storage.py`): thêm `trace_id_search` (LIKE, `max_length~100`, escape `%_`/`\`), `from_ts/to_ts: float ge=0` (filter `started_at` epoch REAL; frontend convert date-input → epoch start/end-of-day, chốt múi giờ local trong comment), `sort_by` whitelist (`started_at|duration_ms|num_spans|total_tokens`) + `sort_dir` (`asc|desc`, default `started_at desc`), sort `duration_ms` đẩy NULL cuối (COALESCE), thêm `total` COUNT cùng WHERE (additive, không gãy client cũ). Giữ `status/min_duration_ms/name_filter/limit/offset` nguyên. Không đụng schema/write path.
2. **Frontend list → bảng** (giữ server shell auth admin, thêm client inner, token pass qua props): shadcn `Table` + sortable headers + column visibility toggle (localStorage) + search trace_id + date from/to + status select + pagination có total (default limit 20→50). Cột từ fields hiện có + copy một chạm (clipboard + fallback).
3. **Frontend detail → 4 tabs** (Tổng quan/Chunks/Memory/Raw; RAGAS gộp thành banner-note trong Tổng quan vì offline): Tổng quan = summary + collapsible waterfall tree thật (map `parent_span_id` O(n), expand/collapse per node, orphan→depth 0, cycle-guard, bar left%+width%+min-width 2px, màu kind/status, click chọn; trace duration 0/None → bar full-width). Chunks = spans tool/llm IO; Memory = attributes; Raw = `JsonBlock` dùng chung + Badge truncated đệ quy.
4. **Span IO + JSON + copy + truncation**: click span mở expandable (`<details>`/accordion nhẹ) hiện inputs/outputs/attributes qua shared `JsonBlock` (export từ `SpanIODetail.tsx`, Raw tab dùng chung — không file `JsonViewer.tsx` riêng) + copy IDs + Badge khi `containsTruncated(v)` đệ quy gặp `...[truncated`. Note "bản full không lưu (truncate 2000 chars)". Không lib nặng.
5. **Tests + gate**: mở rộng `test_traces_api.py` (search/sort/date/total + whitelist reject + backward-compat); `tsc --noEmit` + `eslint` sạch; smoke admin list/detail. Không benchmark.
6. **Batch 2 (plan để sau)**: migration `feedback` + API + tab Đánh giá; comments per node; scores/tags/session/userId/version/env/cost columns; DAG SVG; virtualized chỉ khi >10k rows; row selection; DELETE confirm (để sau vì destructive, không phải vì cần migration).

## Files To Change 6 (Approved — tối đa 4 files mới, gộp JsonViewer theo debate)
- Sửa: `src/interfaces/api/routes/traces.py` (params search/date/sort/total + whitelist), `src/infrastructure/observability/tracing/storage.py` (`list_traces` + COUNT total), `src/tests/unit/infrastructure/observability/test_traces_api.py` (+tests mới), `frontend/src/app/traces/page.tsx` + `frontend/src/app/traces/[id]/page.tsx` (server shell giữ, render client inner).
- Mới: `frontend/src/app/traces/_components/TracesTable.tsx`, `frontend/src/app/traces/[id]/_components/TraceDetailTabs.tsx`, `TraceWaterfall.tsx` (collapsible tree + bars left%/width%), `SpanIODetail.tsx` (export thêm `JsonBlock` dùng chung cho Raw tab — không file `JsonViewer.tsx` riêng).
- Không sửa: `tracer.py`, `models.py`, schema sqlite, eval/RAGAS harness, auth gate, `.env`. Không thêm dep.
- Batch 2 (chưa đụng): alembic feedback/comments, columns scores/tags/session/..., DELETE endpoint, DAG, virtualization.

## Current Status 6
- Phase 2 DONE + verify DONE 15/10/2026 (DB tree 3 tầng, LICENSE MIT ngoài ee/, UI primitives sẵn, truncate 2000 suffix). Phase 3 Plan 6 candidate đã viết (dùng brainstorming, classified bounded).
- Debate DONE 15/10/2026 — REVISE minor 7 điểm ACCEPTED toàn bộ (total+epoch-params, 4 tabs gộp RAGAS, collapsible tree + waterfall left%/min-width, recursive truncation, gộp JsonViewer; xem Debate Notes 6). Plan 6 + Files 6 đã cập nhật Approved. Sẵn sàng implement Batch 1.

## Debate Notes 6 (15/10/2026 — Plan 6 trace UI, verdict REVISE minor)
- Đã đọc: Request/Clarified Scope 6/Constraints 6/Acceptance 6/Library verification 6/Plan 6/Files 6 + code thật `routes/traces.py` (list `limit/offset/status/min_duration_ms/name_filter`, `ORDER BY started_at DESC` cứng, `count=len(rows)` không phải total), `storage.py` (`list_traces` build query string + params, `idx_traces_started` sẵn, `get_trace` spans ORDER BY started_at ASC, `_row_to_span` json.loads có suppress → truncated JSON parse-fail giữ nguyên string), `traces/page.tsx` + `traces/[id]/page.tsx` (Server Components, gate `getServerSession` role admin, list `limit=20` cứng, detail dump `<pre>`), `components/ui/table.tsx` (shadcn table sẵn), `test_traces_api.py` (6 tests, pattern fixture rõ), `tracer.py:244` + `models.py:90` (suffix `...[truncated N chars]`), `cleaner.py:32` (`\n...[truncated]` variant RAG — không thuộc traces).
- (1) Backend params: whitelist `started_at|duration_ms|num_spans|total_tokens` + `sort_dir` đủ, default `started_at desc` = giữ hành vi cũ → backward-compat OK. Không param thừa (mỗi param 1-2 dòng WHERE/ORDER). Thiếu 3 chi tiết: (a) `trace_id_search` cần `max_length` (~100 như name_filter) + escape LIKE `%_`; (b) `from_ts/to_ts` là epoch REAL — phải chốt frontend convert date-input → epoch (start-of-day/end-of-day, múi giờ) trong plan; (c) `duration_ms` NULL (trace running) khi sort + khi vẽ waterfall cần fallback (COALESCE hoặc đẩy NULL cuối + bar full-width). Thêm nữa: pagination thật cần `total` (COUNT query) vì `count` hiện tại = page-size, không phải tổng — thêm field `total` additive, không gãy client cũ.
- (2) Server shell + client inner: ĐÚNG, cách rẻ nhất giữ admin gate (`getServerSession` + redirect chỉ chạy server; convert cả page sang "use client" sẽ mất gate + phải tự xử session). Token truyền xuống client inner qua props là chấp nhận được (đơn giản nhất; không dựng proxy route thêm). Tabs: RAGAS tab placeholder "không có số, chỉ note/link" là anti-pattern — RAGAS là eval offline, không bao giờ có per-trace → GỘP RAGAS note vào tab Tổng quan (banner nhỏ), còn 4 tabs (Tổng quan/Chunks/Memory/Raw). Đủ Acceptance, ít code hơn, Batch 2 mở tab Đánh giá thật khi có feedback.
- (3) Waterfall div bars + indent: ĐỦ ở quy mô thật (489 traces, mẫu lớn nhất 32 spans; kể cả trace to cũng <100 spans → không cần react-window/recharts/virtualized — đúng YAGNI của planner). Phát hiện tree thật (2898/3387 spans có parent, depth 3) NÂNG plan lên được: collapsible tree (expand/collapse per node, build map O(n) ~40 dòng, guard orphan-parent-missing → depth 0 + cycle-guard) thay vì indent tĩnh; fallback "indent theo kind" trong Scope 6 bỏ hẳn (dữ liệu đã chứng minh tree thật). Waterfall cần thêm: left% offset theo `(start-trace_start)/duration` (plan mới chỉ nêu width%), min-width 2px cho span ngắn, fallback trace_duration 0/None (trace running 1 span) → bar full-width.
- (4) Truncation detect suffix `...[truncated`: ĐỦ, không lib nặng. Sửa nhỏ: vì `_row_to_span` parse-fail giữ string ở top-level nhưng field dài bên trong dict có thể truncated lồng nhau → check đệ quy `containsTruncated(v)` (~10 dòng, quét string lồng nhau) thay vì chỉ check top-level. Không un-truncate được (bản full không lưu) — Badge + note "xem full trong JSONL mirror nếu có" là đủ.
- (5) Batch 2 defer ĐÚNG: feedback/comments cần migration (grep không thấy bảng) + scores/tags/session/userId/version/env/cost cần cột mới + DAG SVG layout + virtualized (489 rows → YAGNI rõ) + delete destructive. Không mục Batch 1 nào giấu migration: waterfall/tree (parent_span_id sẵn), tabs (cột sẵn), search/sort/date (cột sẵn), copy/truncation/JSON (hiển thị). Ghi thêm: DELETE không cần migration về kỹ thuật nhưng giữ ở Batch 2 vì destructive — lý do an toàn, không phải schema.
- (6) Files tối giản: `JsonViewer.tsx` riêng là YAGNI — GỘP thành shared `JsonBlock` export trong `SpanIODetail.tsx` (Raw tab + SpanIO cùng import), tối đa 4 files mới (TracesTable, TraceDetailTabs, TraceWaterfall, SpanIODetail). `_components` colocated (underscore = private, không thành route) là đúng convention Next App Router. Pages giữ server shell mỏng (auth + fetch initial + pass token/data), logic còn lại vào client inner.
- Không tìm được plan đơn giản hơn đáng kể ngoài 7 điểm trên: giữ Batch 1/2 split, giữ whitelist/sort/search/date, giữ div-bars, giữ `<details>`/accordion + Badge.

## Next Agent
- reviewer (review Batch 1 traces: backend search/sort/date/total + TracesTable + 4 tabs + waterfall + SpanIO + tests; gate tsc/eslint/unit bên dưới)

## Implementation Notes 6 (implementor 15/10/2026 — Batch 1 DONE)
- Backend: `storage.py` thêm `_escape_like` (escape `\`/`%`/`_`, `ESCAPE '\'`), `_where_clause` dùng chung cho list+count (fix luôn `name_filter` chưa escape trước đây), `_order_clause` (whitelist ở route via Literal; `duration_ms` NULL-cuối bằng `IS NULL ASC`), `count_traces` cùng WHERE; `routes/traces.py` thêm `trace_id_search` (max_length 100), `from_ts/to_ts` (ge=0), `sort_by`/`sort_dir` (default `started_at desc` = hành vi cũ), response thêm `total` additive (`count` giữ = page-size, backward-compat).
- Frontend list: server shell giữ nguyên (admin gate + fetch initial limit=50); client inner `traces/_components/TracesTable.tsx` (shadcn Table, sortable headers 4 cột, visibility localStorage `traces-cols-v1`, search trace_id + date from/to→epoch local start/end-of-day + status, pagination có total default limit 50, copy một chạm clipboard+fallback).
- Frontend detail: server shell giữ; `TraceDetailTabs.tsx` (4 tabs Tổng quan/Chunks/Memory/Raw + banner RAGAS-note trong Tổng quan), `TraceWaterfall.tsx` (buildTree O(n) từ `parent_span_id`, orphan→root depth 0, cycle-guard cả build lẫn render, bars left%+width%+min-width 2px, duration 0/None→full-width, màu kind/error), `SpanIODetail.tsx` (`<details>` expandable + `JsonBlock` dùng chung cho Raw tab + `containsTruncated` đệ quy + copy span ID + Badge).
- Ý tưởng học từ Langfuse MIT (ngoài `ee/`, không copy verbatim) đã ghi trong comment 3 files mới; không thêm dep; không đụng tracer/models/schema/eval/auth/.env. Batch 2 chưa động.
- Files đã đổi (thực tế): sửa `src/infrastructure/observability/tracing/storage.py`, `src/interfaces/api/routes/traces.py`, `src/tests/unit/infrastructure/observability/test_traces_api.py` (+5 tests), `frontend/src/app/traces/page.tsx`, `frontend/src/app/traces/[id]/page.tsx`; mới `frontend/src/app/traces/_components/TracesTable.tsx`, `frontend/src/app/traces/[id]/_components/{TraceDetailTabs,TraceWaterfall,SpanIODetail}.tsx`.

## Current Status 6 (tiếp — IMPLEMENT DONE 15/10/2026)
- Gate: `test_traces_api.py` **11 passed** (6 cũ + 5 mới: total-compat/search-hit-miss/LIKE-escape/date-from-to/sort-whitelist); observability folder **27 passed**; `tsc --noEmit` **sạch (exit 0)**; `eslint` 6 files traces **0 errors** (1 warning unused đã xóa; fix 2 lỗi `set-state-in-effect` bằng lazy useState initializer + fetch tường minh thay vì effect).
- Live smoke admin: **không chạy được** — backend localhost:8000 connection-refused (không có server chạy); cần reviewer/môi trường có backend + login admin để smoke list/detail bằng mắt.
- Batch 2 giữ nguyên để sau (feedback/comments/scores/DAG/virtualized/DELETE).

## Request mới (15/10/2026 — audit việc dang dở, bỏ feedback table)
- User: không cần làm bảng feedback; kiểm tra còn việc nào dang dở/chưa làm thì làm.
- Planner đã đọc WORKFLOW_STATE.md toàn bộ (477 dòng) + đối chiếu repo thực tế (`git status`, `git log`, glob/grep, Test-Path).

## Open Questions (audit — chờ user chốt trong chat)
- (sẽ hỏi trong chat — xem tin nhắn planner kèm theo)

## Constraints (audit)
- Planner: không sửa code ngoài WORKFLOW_STATE.md.
- Không tự ý commit/push khi chưa được user cho phép tường minh (tiền lệ: Plan 2/Plan 4 push chỉ khi user yêu cầu).
- Bỏ feedback table: Batch 2 feedback + tab Đánh giá + comments per node đi kèm feedback schema không làm; các mục Batch 2 còn lại (scores/tags/session/DAG/virtualized/row-selection/DELETE) chờ user xác nhận có bỏ luôn hay giữ.

## Current Status (audit dang dở 15/10/2026 — planner đối chiếu WORKFLOW_STATE vs repo thật)
1. **Uncommitted khổng lồ chưa push:** `git status` = 49 files modified + hàng chục untracked; `git log` dừng ở `488269e` (video move). Các IMPLEMENT DONE sau đó chưa hề commit: education (calculators/tools/tutor/RAG edu), lip-sync (Mascot/SceneView/Trau + media-utils), trace Batch 1 (routes/storage/tests + 4 components mới). Kèm sửa lan rộng chưa rõ thuộc batch nào: market/alert/forecast/sector/portfolio services + adapters + redis/serialization + dependencies + app.py + cli + mcp tools + config + pyproject + .env.example + README + compare_reports + middleware.ts xóa + proxy.ts mới. Untracked: `.dockerignore`, docs (news_spike/pilot/full_outline), evals (duplicates/rag_metrics/news_eval/datasets), market_store/, sentiment/, rss_adapter, education, contract test, frontend.dev.log, trau-video audio M3L2 (9 mp3 + durations.json).
2. **Rates Layer-2 SQL store (spec 14/10/2026, 6 nhóm):** chưa có file nào (`src/infrastructure/rates*` không tồn tại); chỉ có `market_store/` pilot. Đây là việc lớn duy nhất chưa hề implement.
3. **Reviewer + smoke treo:** lip-sync Next=reviwer chưa review; trace Batch 1 Next=reviewer + live smoke admin FAIL (localhost:8000 refused) chưa smoke lại bằng mắt.
4. **Curriculum JSON bị ignore:** `data/lessons/curriculum_tai_chinh_ca_nhan.json` tồn tại local nhưng `.gitignore: data/` chặn → link README đúng local, sai remote (caveat Plan 2, chờ user quyết exception).
5. **Video M3L2 vẫn draft:** placeholder số chưa điền (--force); `out/M3L2.mp4` + audio tồn tại local nhưng `trau-video/out/` ignore → chưa có bản final, chưa commit được.
6. **WORKFLOW_STATE.md itself untracked** (`?? WORKFLOW_STATE.md`) — source-of-truth nằm ngoài git; các push trước không kèm nó.
7. **Suite xanh chưa re-verify sau đống uncommitted:** lần xanh gần nhất 769 passed (Phase A) / 27 observability (Batch 1); chưa có full-suite sau hiện trạng.

## Clarified Scope 7 (15/10/2026 — user trả lời audit, chốt làm dang dở)
- Diễn đạt lại: dọn dứt điểm việc treo theo thứ tự — (A) review/commit/push đống hiện tại trước, (B) rồi làm việc lớn nhất (rates Layer-2 SQL store 6 nhóm), kèm feedback table (Batch 2, user đổi ý: vẫn làm), e2e + smoke mắt cho traces, track file bị ignore.
- (A) Review/commit/push: review `git status/diff` (49 modified + untracked), stage có chọn lọc (không `add -A`, không secrets/.env/DB/qdrant/traces/audio/out/log/node_modules), commit theo repo style, push main, báo hash. Bao gồm track `data/lessons/curriculum_tai_chinh_ca_nhan.json` + `WORKFLOW_STATE.md` qua exception `.gitignore` (user yêu cầu).
- (B1) Rates Layer-2 giữ nguyên spec 6 nhóm cũ: huy động niêm yết daily (giữ 6–12th), cho vay niêm yết weekly/khi đổi, bình quân SBV monthly (vĩnh viễn), điều hành SBV (vĩnh viễn + effective_date), VNIBOR daily (3–6th), metadata NH (lâu dài); không lưu HTML thô/intermediate/thỏa thuận; cache SQL-first (stale >12–24h huy động />1th SBV / force_refresh / hash đổi) + `crawled_at` + `source`. Mirror pattern `market_store/` (sqlite stdlib, WAL, RLock, UTC ISO), không thiết kế mới.
- (B2) Feedback vẫn làm: migration + API + UI tab chấm tay cạnh RAGAS (Batch 2 đã plan), không cắt.
- (B3) Xong mới coi là xong: dựng backend + login admin smoke bằng mắt traces list/detail + test e2e (không chỉ unit/tsc/eslint).
- Video M3L2 giữ draft (placeholder số chưa điền); không nhận final trong đợt này.

## Constraints 7
- Mirror `market_store/` cho rates (stdlib sqlite only, WAL, RLock, UTC ISO, DB dưới `data/` gitignored); không thêm dep mới nếu native đủ.
- Không copy Langfuse verbatim; admin-only traces giữ nguyên; PIT/thuế/lãi suất ghi nguồn + ngày hiệu lực.
- Commit/push chỉ sau review diff (không secrets, không DB/audio/out/log/node_modules); không force-push/amend-fail.
- Planner không sửa code ngoài WORKFLOW_STATE.md.

## Acceptance Criteria 7
1. Git sạch sau (A): `git status` chỉ còn ignored + files chủ ý để lại; push main OK, báo hash; curriculum JSON + WORKFLOW_STATE.md đã track (link README đúng remote).
2. Rates store chạy được: 6 nhóm bảng đúng retention/effective_date, SQL-first + stale/force/hash, `crawled_at`+`source`, unit số tay + ingest thật ít nhất 1 nhóm, tool đọc được.
3. Feedback chạy được: migration + API POST/GET + tab UI cạnh RAGAS, unit + smoke tay.
4. Traces e2e + smoke mắt: backend up, login admin, list/detail đúng bằng mắt + e2e test mới pass.
5. Suite: full unit không regression (so baseline), `tsc --noEmit` + `eslint` sạch.

## Library verification 7 (15/10/2026 — planner verify trước Plan 7)
- `market_store/store.py:1-68` đọc thật: sqlite stdlib only + `threading.RLock` + `PRAGMA journal_mode=WAL` + `_SCHEMA executescript` + UTC ISO (`datetime.now(timezone.utc).isoformat()`) + DB dưới `data/` (gitignored). Rates store mirror y hệt → không dep mới, không context7 ngoài stdlib (pattern nội bộ đã đủ).
- Frontend traces mới đọc thật (`TracesTable.tsx:1-60`): `"use client"` + shadcn Table + copy clipboard+fallback + date→epoch local — e2e/smoke chỉ cần backend + admin login sẵn có (`login/page.tsx` hint admin@finsight.vn), không framework mới.
- Gitignore verify thật: `git check-ignore -v` 15/10/2026 → curriculum JSON **bị ignore** bởi `.gitignore:39 data/`, `WORKFLOW_STATE.md` **không bị ignore** (chỉ untracked). Git docs (git-scm.com/docs/gitignore) + NOTES: không re-include được file khi parent dir bị exclude → với `data/` phải un-ignore parent trước; cách chuẩn là đổi `data/` → `data/*` rồi `!data/lessons/` + `!data/lessons/curriculum_tai_chinh_ca_nhan.json`, xong verify lại bằng `git check-ignore -v` (DB/audio/out/log vẫn ignore). Implementor tự verify, không đoán mò.

## Plan 7 (Approved sau debate 15/10 — REVISE đã tiếp thu, xem Debate Notes 7)
1. **(A) Review/commit/push — thematic 3–4 commits, cấm `add -A`:** `git diff --stat` triage từng file về đúng batch (không rõ → giữ lại); chạy **full unit baseline TRƯỚC commit đầu** (ghi số so 769/27); track giữ nguyên `data/` + `git add -f data/lessons/curriculum_tai_chinh_ca_nhan.json` + `git add WORKFLOW_STATE.md` thường; commits (i) edu+RAG (ii) video lip-sync (iii) traces Batch1 (iv) infra lan rộng tách riêng — mỗi commit review diff + suite liên quan xanh; verify 2 chiều `git check-ignore -v` + `status --porcelain` trước mỗi add (curriculum hết ignored, DB/audio/out/log vẫn ignored); push từng nhịp, báo hash.
2. **(B1) Rates 2 nhịp, pilot policy-SBV:** nhịp 1 = `rates_store/store.py` (6 bảng + hằng retention per-table + đủ `date/effective_date/crawled_at` + `source` + `purge_*`) + `ingest.py` (pilot duy nhất policy SBV static, `generic_html`) + unit (retention/stale/hash/read-through) + ingest thật + verify SQL. Nhịp 2 (chỉ khi nhịp 1 xanh) = `cached_adapter` (SQL-first, stale 12–24h/>1th, `force_refresh`) + 1 tool `get_rates(group,bank?,from,to,force_refresh?)` + scheduler opt-in để cuối.
3. **(B2) Feedback admin-only:** `storage.py` `_SCHEMA` thêm `feedback(trace_id,span_id NULL,score,comment,author,created_at)` IF NOT EXISTS + index `trace_id` + CHECK `score` + author=admin username (không alembic — alembic chỉ quản User/postgres); routes POST/GET admin-only (`get_current_admin_user`); frontend tab Đánh giá cạnh RAGAS; tests + smoke tay.
4. **(B3) E2E tách smoke, không playwright:** e2e TestClient DB temp trước (list search/sort + detail tree + feedback POST/GET); smoke mắt sau (backend up + admin@finsight.vn theo checklist list/detail trong Debate Notes 7).
5. **Gate:** full unit + `tsc` + `eslint` sạch → push từng nhịp → báo hash.

## Files To Change 7 (Approved — thematic commits + add -f, rates 2 nhịp, không playwright)
- Track (không sửa `.gitignore`): `git add -f data/lessons/curriculum_tai_chinh_ca_nhan.json`, `git add WORKFLOW_STATE.md` thường.
- Mới nhịp 1: `src/infrastructure/rates_store/{__init__,store,ingest}.py`, `src/tests/unit/infrastructure/rates_store/test_*.py`.
- Mới nhịp 2 (sau nhịp 1 xanh): `cached_adapter.py` (+scheduler opt-in), `src/mcp_server/tools/rates.py` (1 tool `get_rates`), e2e `src/tests/e2e/test_traces_e2e.py` (TestClient, không playwright).
- Sửa feedback: `tracing/storage.py` (feedback + index + CHECK), `routes/traces.py` (POST/GET admin-only), frontend detail tab Đánh giá, `README.md`/docs ngắn.
- Không làm: gitignore rewrite, scheduler/MCP nhịp 1, 6 tools riêng, playwright, scores/tags/DAG/virtualized.
- Không sửa: tracer write semantics, eval harness, `.env` secrets.

## Debate Notes 7 (15/10/2026 — Plan 7 audit/rates/feedback/e2e, verdict REVISE)
- Đã đọc: Request/Clarified Scope 7/Constraints 7/Acceptance 7/Library verification 7/Plan 7 candidate/Files 7 + đối chiếu thật `.gitignore` (`data/` dòng 39), `market_store/store.py` (stdlib sqlite + RLock + WAL + 2 tables + meta, DB dưới `data/`), `market_store/scheduler.py` (opt-in `ENABLE_MARKET_SCHEDULER`), `alembic/env.py` (chỉ migrate `User`/postgres via `DATABASE_URL`, không đụng traces sqlite), `routes/traces.py` (admin-only `get_current_admin_user`), `tracing/storage.py` (`_SCHEMA` executescript IF NOT EXISTS, chưa có feedback), repo không có playwright.
- (A1) 1 commit cho 49 modified + untracked spanning edu/video/trace/infra = khó revert, khó review, 1 batch hỏng phải revert cả 3. Chốt **thematic commits (3–4, không gộp)**: (i) edu+RAG, (ii) video lip-sync, (iii) traces Batch 1, (iv) infra/fixes lan rộng nếu không xếp được vào 3 nhóm trên thì tách riêng — mỗi commit verify suite liên quan xanh trước khi commit tiếp. Cấm `add -A`.
- (A2) `.gitignore` `data/` → `data/*` là rủi ro lộ DB: đổi pattern là mở toàn bộ `data/` thành candidate, chỉ an toàn nếu blocklist `*.db/*.sqlite/qdrant*/traces//*.mp3/*.mp4/out//*.log` đầy đủ + verify `git check-ignore -v` 2 chiều (curriculum NOT-ignored + traces.db/market_store.db/qdrant VẪN ignored) + `git status --porcelain` trước mỗi add. Ponytail: với chỉ 1 file cần track, **giữ nguyên `data/` + `git add -f data/lessons/curriculum_tai_chinh_ca_nhan.json`** là tối giản, zero-leak, không sửa gitignore. Chỉ làm `data/*` rewrite nếu user muốn track cả thư mục lessons về sau.
- (A3) Thiếu triage + baseline trước commit: đống lan rộng (market/alert/forecast/sector/portfolio, redis/serialization, dependencies, app.py, cli, mcp, pyproject) chưa rõ thuộc batch nào — phải `git diff --stat` phân loại từng file về đúng thematic commit, file nào không rõ thì giữ lại không commit. Full unit phải chạy TRƯỚC commit đầu tiên (baseline hiện trạng), không phải sau.
- (B1a) Mirror `market_store` đúng hướng (stdlib/WAL/RLock/UTC/DB dưới `data/`), nhưng schema 2 bảng pilot không đủ mẫu cho 6 nhóm retention khác nhau: plan nêu `purge_*` nhưng chưa chốt tham số retention ở đâu (constants per-table), chưa phân biệt `effective_date` (ngày hiệu lực chính sách SBV) vs `crawled_at` (ngày fetch) vs `date` (ngày snapshot) — policy table bắt buộc cả 3. Ingest 6 nguồn parse khác nhau (SBV static vs web NH vs CafeF) — hash/change-detect là chưa đủ, phải chốt group pilot duy nhất: **policy SBV static trước** (nhỏ nhất, retention vĩnh viễn = không purge risk, đã có `generic_html` từ Phase B).
- (B1b) Scheduler + `cached_adapter` + MCP wiring ngay trong cùng batch là thừa: `market_store` scheduler opt-in sau khi ingest tay ổn. Cắt thành 2 nhịp: nhịp 1 = store + ingest + unit + ingest thật 1 nhóm (policy) + verify SQL; nhịp 2 (chỉ khi nhịp 1 xanh) = `cached_adapter` SQL-first/stale + tool đọc. Tool `get_rates` tối thiểu: **1 hàm** `(group, bank?, from, to, force_refresh?)`, không 6 tools riêng (YAGNI).
- (B2) `IF NOT EXISTS` trong `tracing/storage.py` là ĐÚNG, không bắt buộc alembic: `alembic/env.py` chỉ quản lý `User`/postgres, traces.db là sqlite file riêng do `executescript` quản lý từ đầu — nhét feedback vào alembic là sai DB. Thiếu: index `trace_id`, CHECK `score` range, `author` lấy từ admin user (không free-text), `span_id NULL` semantics. API **admin-only** (giữ `get_current_admin_user` như 2 endpoints traces hiện có); mở cho mọi user cần rate-limit/abuse guard = ngoài scope.
- (B3) TestClient API-level + smoke mắt là ĐỦ, không thêm playwright: repo chưa có playwright/e2e infra, thêm mới = dep + browser + CI nặng + flaky cho trang admin CRUD-read đơn giản. Smoke mắt cần checklist tường minh thay vì "đúng bằng mắt": list (sort 4 cột, search hit/miss, date from/to, pagination total, visibility persist, copy), detail (4 tabs render, waterfall expand/collapse + left%/width%, click span IO, truncated Badge, feedback POST/GET roundtrip). Tách e2e (không cần server, chạy trước) khỏi smoke mắt (cần backend + admin login, chạy sau).
- (Thứ tự) A→B1→B2→B3 là ĐÚNG: A dọn baseline trước, B1 (rates lớn nhất) trước B2/B3. B1 trước A sẽ trộn code mới vào đống uncommitted = commit nửa vời, bác bỏ.
- Ponytail cắt: gitignore rewrite → `add -f`; rates scheduler/MCP/docs dồn nhịp 2; 6 tools → 1 `get_rates`; playwright → không; RAGAS tab đã gộp (giữ).

## Current Status 7
- Debate DONE 15/10/2026 — verdict REVISE (xem Debate Notes 7). Plan 7 + Files 7 đã sửa Approved theo toàn bộ điểm debate (thematic commits + add -f + baseline trước commit + rates 2 nhịp pilot-policy + feedback admin-only + e2e tách smoke, không playwright). Sẵn sàng implement A→B1→B2→B3.
- **IMPLEMENT DONE 15/10/2026** — đủ A→B1→B2→B3 (máy), smoke mắt blocked (ghi rõ bên dưới).
- **(A) Review/commit/push DONE:** baseline full unit TRƯỚC commit đầu = **774 passed / 0 failed**; 4 thematic commits (cấm `add -A`, scan secret từng nhịp, DB/audio/out/log vẫn ignored, verify `check-ignore` 2 chiều: curriculum staged qua `-f`, `traces.db`/`market_store.db` vẫn ignored):
  - `faa231e` edu+RAG (calculators/tutor/RAG sources/eval datasets + WORKFLOW_STATE.md + curriculum JSON via `add -f`, giữ nguyên `data/`)
  - `adb374b` video lip-sync (Mascot/SceneView/Trau + media-utils)
  - `c81a0d5` traces Batch 1 (routes/storage/tests + 4 components)
  - `4c6b7c0` infra lan rộng (vnstock v4 + ratio wiring + 43-fixes + news sentiment + market_store pilot + proxy.ts)
  - Push `488269e..4c6b7c0 main -> main`, không force/amend. Cố ý để lại untracked: `frontend.dev.log` (rác), `evals/dashboard/v1/report-gpt41.json` (artifact), `trau-video/public/audio/` (build).
- **(B1) Rates DONE, push `a3c8e9c`:** `rates_store/store.py` (6 bảng + `RETENTION_MONTHS` per-table 12/12/None/None/6/None + `date/effective_date/crawled_at` + `source` + `purge_older_than/purge_expired` + `is_stale/latest_fetch` + meta) + `ingest.py` (pilot duy nhất policy SBV static, `generic_html` + seed fallback, hash-skip, QĐ 1123/HL 19/06/2023) + `cached_adapter.py` (SQL-first, stale 24h/168h/720h, policy tự refresh, shape `data_as_of/source/stale`) + `scheduler.py` (opt-in `ENABLE_RATES_SCHEDULER`, weekly) + 1 tool `get_rates` (đăng ký `tools/__init__.py`, tutor allowlist giữ nguyên) + README (19 tools + row `get_rates`).
  - Unit rates **12 passed** (parse số tay 4.5/3.0/5.0, retention constants, latest/source/dates, hash-skip, fallback seed, purge, stale, adapter shape/error/empty). Count tests 18→19.
  - Ingest thật: fetch **luatvietnam.vn thật thành công** (source=URL thật, không seed) → 3 rows `policy_rates` HL 2023-06-19 trong `data/rates_store.db`; chạy lại → `skipped: True` (hash).
- **(B2) Feedback DONE, commit `0a3316b`:** `storage.py` `_SCHEMA` += `feedback(trace_id,span_id NULL,score,comment,author,created_at)` IF NOT EXISTS + `CHECK (score BETWEEN 1 AND 5)` + index `trace_id` (đúng chỗ: alembic chỉ quản User/postgres) + `add_feedback/list_feedback`; routes POST/GET admin-only (`get_current_admin_user`, author=admin email, 422 ngoài 1–5, 404 trace lạ); frontend tab **Đánh giá** cạnh RAGAS-note (5 tabs) — server shell fetch initial + client reload sau submit, không fetch trong effect (né rule `set-state-in-effect` mới thành error). Tests feedback **3 passed**, observability folder **30 passed**.
- **(B3) E2E DONE 3/3** (`src/tests/e2e/test_traces_e2e.py`, TestClient DB temp, admin@finsight.vn): list search/sort/total + detail tree depth (root → 2 children) + feedback roundtrip.
- **Gate:** full unit **789 passed / 0 failed** (= 774 baseline + 12 rates + 3 feedback), e2e 3/3 riêng, `tsc --noEmit` sạch, `eslint src/app/traces` 0 errors 0 warnings.
- **Smoke mắt BLOCKED (không đoán, cần người):** backend cold-boot torch quá 80s chưa lên `/health` (job log: `Started server process`, kẹt `Waiting for application startup`; redis missing nhưng degraded OK); session tool kill process nền nên không giữ server chạy xuyên lệnh. Checklist smoke cho người (backend up + login admin@finsight.vn): list sort 4 cột/search hit-miss/date/pagination total/visibility persist/copy; detail 5 tabs, waterfall expand/collapse, click span IO, truncated Badge, feedback POST/GET roundtrip.
- Video M3L2 giữ draft (không nhận final).

## Implementation Notes 7 (implementor 15/10/2026)
- Baseline 774 (đã gồm Batch 1 traces + edu) — khớp 769 Phase A + 5 traces mới.
- `git check-ignore`: curriculum chỉ stage được qua `-f` (parent `data/` excluded, không rewrite gitignore theo debate A2); WORKFLOW_STATE `git add` thường (chưa từng ignore, chỉ untracked).
- Rates `purge_expired` dùng 30d/tháng approx (`ponytail:` trong code — per-table day-count nếu cần chính xác).
- `get_rates` không vào tutor allowlist (giữ Scope 3: tutor = 4 edu + knowledge + chart_spec).
- FeedbackTab: lần 1 dùng `useEffect` fetch-on-mount → eslint error (rule v6 flat-config nâng thành error) → chuyển initial-fetch về server shell + reload sau submit (đúng pattern TracesTable).
- Test count name `test_mcp_has_13_tools` đã stale từ trước (assert 18) — chỉ update số 19 + expected set, không rename (ngoài scope).

## Next Agent
- reviewer (review A→B3: 6 commits faa231e/adb374b/c81a0d5/4c6b7c0/a3c8e9c/0a3316b + WORKFLOW_STATE; gate số bên trên; smoke mắt checklist chờ người)

## Request mới (15/10/2026 — rà soát sót chưa triển khai)
- User: rà soát xem còn sót gì chưa triển khai không.
- Planner đã đọc WORKFLOW_STATE.md đuôi (Current Status 7 + Notes 7, tổng 580 dòng) + đối chiếu repo thật: `git log/status`, `rates_store/` + đếm rows sqlite, grep `get_rates|rates_store|ENABLE_RATES_SCHEDULER`, grep placeholders lessons, kiểm tra Batch 2/Phase 4b/reviewer/smoke.

## Open Questions (audit sót — chờ user chốt trong chat)
- (sẽ hỏi trong chat — xem tin nhắn planner kèm theo)

## Constraints (audit sót)
- Planner: không sửa code ngoài WORKFLOW_STATE.md.
- Không tự ý mở rộng scope (5 nhóm rates rỗng, Batch 2 còn lại, Phase 4b, video final) khi user chưa chốt.
- M3L2 + lessons giữ draft cho tới khi số [[TÍNH BẰNG CÔNG CỤ]] được điền bằng education tools đã kiểm tra.

## Current Status (audit sót 15/10/2026 — đã đối chiếu WORKFLOW_STATE vs repo thật)
- ĐÃ XONG (không sót): A 4 thematic commits push tới `8c75304` (git chỉ còn 3 untracked cố ý: report artifact/dev.log/audio build); rates 6 bảng + `get_rates` + scheduler opt-in + README; feedback table/API/tab Đánh giá; e2e 3/3; gate 789/0 + tsc + eslint.
- SÓT 1 (lớn): rates 5/6 nhóm rỗng — sqlite đếm thật: `policy_rates`=3 rows, `deposit_listed`/`lending_listed`/`avg_rates_monthly`/`vnibor_daily`/`banks_meta`=0 rows. Đúng Plan 7 nhịp 1 (pilot policy duy nhất), nhưng spec 6 nhóm gốc coi như chưa full data (cần parser riêng web NH/CafeF/SBV-monthly, không chỉ hash-skip).
- SÓT 2 (treo, cần người/môi trường): smoke mắt BLOCKED (backend cold-boot torch >80s chưa `/health`, session kill process nền) + reviewer A→B3 chưa review.
- SÓT 3 (Batch 2 còn lại, ngoài feedback đã xong): scores/tags/session/userId/version/env/cost columns, comments per node riêng, graph DAG, virtualized hover-prefetch, row selection, DELETE dialog — chưa động.
- SÓT 4 (cũ): Phase 4b full pipeline (toàn sàn + intraday + postgres) mới outline `docs/pipeline_full_outline.md`, chưa implement.
- SÓT 5 (video): M3L2 + ~30 lessons còn `[[TÍNH BẰNG CÔNG CỤ]]`/`type:placeholder` (grep lessons: M3L2 2 chỗ + M6L1/M3L4/…nhiều file; `index.json` open_placeholders 1–3 ở đa số bài) — giữ draft theo chốt, chưa điền số + chưa render final.
- NHỎ (ghi nhận, không block): test name stale `test_mcp_has_13_tools` (assert 19); `purge_expired` approx 30d/tháng (đã mark `ponytail:`); `get_rates` ngoài tutor allowlist (by design); 3 untracked cố ý để lại.

## Request 8 (15/10/2026 — user chốt vét sót, scope lớn)
- User trả lời audit 5 điểm: (1) ingest tiếp 5 nhóm rates rỗng (parser riêng web NH/CafeF/SBV-monthly); (2) Batch 2 còn lại làm tiếp; (3) smoke thử lại cách khác (tăng timeout/chạy nền khác) + duyệt reviewer luôn; (4) Phase 4b full pipeline tính vào đợt này; (5) video placeholders điền số bằng tools rồi render final, bắt đầu từ M1L1.
- Planner diễn đạt lại: vét toàn bộ sót thành một đợt — rates full 6 nhóm có data thật + Batch 2 hoàn thiện traces + smoke/reviewer dứt điểm + Phase 4b full pipeline + video M1L1 final (điền số bằng education calculators đã kiểm tra). Đây là đợt lớn nhất từ đầu (gộp 5 luồng độc lập), phải chia nhịp + chốt acceptance từng nhịp trước khi plan chi tiết.

## Open Questions 8 (chờ user — hỏi trong chat kèm theo)
- (xem tin nhắn planner kèm theo — 6 câu follow-up)

## Constraints 8
- Planner: không sửa code ngoài WORKFLOW_STATE.md.
- Không benchmark full nếu user không yêu cầu explicitly (tiền lệ các batch trước hoãn benchmark, chỉ unit + smoke).
- Không commit secrets/DB/audio/out/log/node_modules; không force-push/amend-fail; stage có chọn lọc.
- Mirror pattern sẵn có (`market_store/` cho rates, `TraceStore` IF NOT EXISTS cho traces columns) thay vì thiết kế mới khi có thể; không thêm dep nặng nếu native đủ.

## Clarified Scope 8 (chốt 15/10/2026 — user trả lời 5 điểm + debate phần còn lại)
- User chốt: (2) Batch 2 làm cả 6 + được thêm cột nullable + DELETE có làm; (3) Phase 4b full luôn; (4) mp4 giữ local; (5) được chạy docker compose; (6) chưa benchmark, thứ tự rates → Batch 2 → smoke/reviewer → Phase 4b song song video. Phần chưa trả lời giao debate chọn tối ưu (planner đề xuất dưới, debater quyết).
- R1 rates full (planner đề xuất tối ưu): ưu tiên SBV-monthly + CafeF trước (aggregator ổn định hơn crawl lẻ từng NH), fallback web 3–4 NH lớn (VCB/BIDV/Vietin/ACB) rồi seed đã verify khi WAF/DNS chặn (pattern Phase B); acceptance tối thiểu: deposit ≥3 NH × 4 kỳ hạn, lending ≥3 NH, avg_monthly ≥1 kỳ SBV, vnibor ≥5 kỳ hạn, banks_meta ≥5 NH (debater chốt số).
- R2 Batch 2 cả 6 đã chốt; scores/tags/session/userId/version/env/cost thêm cột nullable vào `traces` (SQLite ALTER ADD COLUMN, backfill null, không alembic vì traces.db sqlite riêng).
- R3 smoke (đề xuất): docker compose up -d (detached, không bị session kill) + start_period/timeout 10 phút cho torch cold-boot + checklist Status 7; reviewer = code review + approve push.
- R4 Phase 4b full (đề xuất chia nhịp trong full): nhịp 1 daily toàn sàn (HOSE+HNX+UPCoM 2–3 năm, chunked-resumable) → nhịp 2 intraday VN30 pilot (không full intraday toàn sàn ngay) → nhịp 3 postgres + cron ngoài; acceptance đề xuất: coverage ≥95% HOSE+HNX daily 2 năm, hit-rate read-through ≥90%, freshness daily T+1 (debater chốt).
- R5 video M1L1 (verify thật 15/10: 8 scenes, VO 0 `[[...]]`, `illustrative_numbers`=null, status `draft_ready_for_review`, V1 label minh họa required + V2 recompute/V3 human-review open): final = verify số học trong narration bằng budget tool + giữ nhãn minh họa + TTS + render Remotion, mp4 local only, user duyệt V3 mới gọi là final.

## Acceptance Criteria 8 (chốt)
1. Rates 6/6 nhóm có rows đạt tối thiểu R1, `get_rates` đúng từng nhóm, nguồn + ngày hiệu lực rõ; unit + ingest thật pass.
2. Batch 2 đủ 6 tính năng, unit/tsc/eslint xanh, không regression (so 789 baseline).
3. Smoke docker-compose pass checklist + e2e pass; reviewer APPROVE (code + push).
4. Phase 4b đạt ngưỡng R4 (debater chốt số cuối).
5. M1L1: 0 placeholder, mp4 local OK, số khớp tools, V3 human duyệt.
6. Không benchmark full; push từng nhịp, báo hash.

## Library verification 8 (15/10/2026 — planner verify trước Plan 8)
- Postgres/docker (đọc thật): `postgres:16-alpine` + `pg_isready` healthcheck đã có cả compose prod/dev; `DATABASE_URL/DATABASE_SYNC_URL` asyncpg/postgres đã wiring; `psycopg2-binary + alembic` đã pin trong `pyproject.toml`; backend command chạy `alembic upgrade head` trước uvicorn — Phase 4b postgres không cần dep mới, chỉ migration + compose đã sẵn.
- Rates (đọc thật): `rates_store/{store,ingest,cached_adapter,scheduler}.py` tồn tại; pilot policy SBV dùng `generic_html` + seed fallback (SBV gốc WAF-block, CIC DNS fail — pattern Phase B) — 5 nhóm còn lại spike tương tự, ưu tiên aggregator trước theo đề xuất R1.
- Traces (đọc thật): `traces`/`spans` chưa có scores/tags/session/...; `feedback` đã có (CHECK 1–5 + index) — Batch 2 thêm cột nullable qua SQLite ALTER ADD COLUMN là backward-compat, không đụng alembic (alembic chỉ quản User/postgres).
- Video (đọc thật M1L1): 8 scenes, VO 0 placeholder, `illustrative_numbers`=null, status `draft_ready_for_review`, V2/V3 open — final M1L1 chủ yếu là verify + TTS + render, mp4 local only (out/ ignore giữ nguyên).

## Plan 8 (Approved sau debate 15/10 — REVISE 6 điểm đã tiếp thu, xem Debate Notes 8)
1. **R1 rates full 5 nhóm (spike tuần tự, seed-fallback tính đạt):** SBV-monthly + vnibor trước → deposit/lending web NH sau (CafeF trước, web 3–4 NH lớn sau); live là ưu tiên không bắt buộc — đạt bằng `seed:*` đã verify khi WAF/DNS chặn (ghi rõ source). Acceptance tối thiểu: deposit ≥3 NH×4 kỳ hạn / lending ≥3 NH / avg ≥1 kỳ / vnibor ≥5 kỳ / banks_meta ≥5 NH. Không đổi schema 6 bảng. Unit + ingest thật + `get_rates` verify.
2. **R2 Batch 2 (DELETE cuối):** cột nullable + comments per node + row selection + DAG SVG nhẹ nội bộ (không lib) trước; virtualized conditional (chỉ khi đo >10k rows, mặc định giữ div + pagination); DELETE admin-only + confirm để cuối. Unit + tsc/eslint.
3. **R3 smoke + reviewer:** `docker compose up -d` (timeout 10 phút: backend start_period 240s + mcp 180s có sẵn) + 1 retry khi dockerd WSL restart + login admin smoke theo checklist Status 7 → reviewer duyệt code + approve push.
4. **R4 Phase 4b full (3 nhịp, coverage HOSE+HNX):** (a) daily HOSE+HNX 2–3 năm chunked-resumable (loại UPCoM khỏi gate 95%); (b) intraday VN30 pilot; (c) postgres + cron ngoài. Gate: VN30→HOSE xanh mới mở HNX/UPCoM; hit-rate ≥90%, freshness T+1.
5. **R5 video M1L1 final local (thu nhỏ):** V2 1-call budget-tool verify S3 (12→6/3.6/2.4) + giữ nhãn minh họa (V1) → TTS edge-tts → render Remotion → verify 0 placeholder + mp4 local (không push, không sửa VO/scenes JSON) → user duyệt V3.
- Thứ tự (giữ ý user): rates → Batch2 → smoke/reviewer → Phase4b ∥ video (R5 không chạy sớm trước R1/R2 để giữ ưu tiên việc lớn nhất; implementor được kéo R5 sớm opportunistic chỉ khi chờ đợi_docker/ingest).

## Files To Change 8 (dự kiến)
- R1: sửa `rates_store/ingest.py` (+parser/nhóm mới), `store.py` nếu thiếu index, `tools/rates.py` nếu mở rộng params, `tests/unit/infrastructure/rates_store/*`, `README.md` (nguồn + số rows).
- R2: sửa `tracing/storage.py` (ALTER ADD COLUMN + comments methods), `routes/traces.py` (+scores/comments/DELETE endpoints admin-only), frontend traces (`TraceDetailTabs`, waterfall/DAG, table selection/virtualized, delete dialog), tests + `test_traces_e2e.py`.
- R3: `docker-compose.yml/dev` nếu thiếu timeout/healthcheck, docs smoke checklist (ghi WORKFLOW_STATE, không file mới nếu không cần).
- R4: `market_store/*` (mở rộng toàn sàn + intraday), `alembic/versions/*` (postgres migration nếu cần), scheduler/cron wiring, `docs/pipeline_full_outline.md` cập nhật, eval coverage script nếu cần (không benchmark full).
- R5: `frontend/trau-video/scripts/*` (tts/render), `public/lessons/M1L1_scenes.json` (chỉ khi điền số — nếu VO đã sạch thì không sửa), `public/audio/M1L1/*` + `out/M1L1.mp4` local (ignored, không commit).
- Không sửa: `.env` secrets, eval harness (chưa benchmark).

## Debate Notes 8 (15/10/2026 — Plan 8 vét sót, verdict REVISE minor)
- Đã đọc: Request 8, Scope 8, Constraints 8, Acceptance 8, Library verification 8, Plan 8, Files 8, Current Status 8 + code thật `rates_store/{store,ingest,cached_adapter,scheduler}.py`, `tracing/storage.py:181-182` (đã có DELETE spans/traces nội bộ), `docker-compose.yml` (backend start_period 240s, mcp 180s), `docs/pipeline_full_outline.md` (toàn sàn 5–6M rows/0.9GB, backfill 2 ngày guest/9h community), `M1L1_scenes.json` (8 scenes, VO 0 placeholder, S3 đã có 6/3.6/2.4tr, S8 nhãn minh họa, V1 required/V2+V3 open).
- (1) R1 acceptance rủi ro WAF/DNS: SBV gốc WAF-block + CIC DNS-fail đã chứng minh ở Phase B/B1 (ingest.py seed fallback). Đặt acceptance cứng "deposit ≥3 NH × 4 kỳ hạn live" mà không chốt seed-fallback đạt = plan dễ kẹt. Sửa: giữ số tối thiểu nhưng cho phép đạt bằng seed-đã-verify khi fetch live bị chặn (ghi rõ source=seed:*), live là ưu tiên không phải bắt buộc. Parser 5 nhóm song song = 5 lần debug WAF/layout cùng lúc; rẻ hơn: spike tuần tự SBV-monthly + vnibor trước (nguồn tập trung, 1 layout), deposit/lending web-NH sau (mỗi NH 1 layout). Không đổi schema 6 bảng (đúng).
- (2) R2 virtualized YAGNI rõ: 489 traces, mẫu lớn nhất 32 spans — div + pagination Batch 1 đủ, virtualized chỉ code khi đo được >10k rows (giữ trong plan dạng conditional, không implement mặc định). DAG không lib nặng: SVG nhẹ nội bộ đủ (đã ghi "không lib nặng" là đúng, giữ). DELETE: `storage.py` đã có DELETE nội bộ 2 dòng → chỉ thêm endpoint admin-only + confirm dialog, rủi ro thấp nhưng vẫn để CUỐI Batch 2 (sau khi columns/comments/DAG/selection xanh) để không lẫn destructive vào nhịp verify đầu.
- (3) R3 compose detached + 10 phút ĐỦ: backend start_period 240s + mcp 180s đã có sẵn trong compose (đọc thật), 10 phút = margin ~2× cold-boot torch. Giữ nguyên, cộng 1 dòng retry khi WSL dockerd restart (~10 phút, đã ghi ở Status Docker packaging) — fail lần 1 do daemon thì `docker compose up -d` lại, không coi là smoke fail.
- (4) R4 quá lớn nếu làm 1 đợt không gate: outline 5–6M rows + backfill 2 ngày guest là việc nền dài nhất repo. Cắt intraday-full → VN30 pilot như Plan đã nêu là ĐÚNG, giữ. Ngưỡng đề xuất hợp lý với 1 уточнение: coverage ≥95% chỉ áp HOSE+HNX (loại UPCoM — thanh khoản thưa, delisted nhiều, outline đã nêu delisted-mark), hit-rate ≥90% + freshness T+1 giữ nguyên. Gate giữa nhịp: nhịp-a daily VN30→HOSE xanh mới mở rộng HNX/UPCoM (mỗi nấc re-validate như outline mục 1).
- (5) R5 M1L1 không còn gì để "điền số": VO 0 placeholder, số duy nhất S3 (12tr → 6/3.6/2.4) là phép nhân 1 dòng, verify bằng 1 call budget tool là xong; `illustrative_numbers=null` + V1 label đã có ở S8. Final M1L1 = V2 recompute 1 dòng + TTS + render + V3 human duyệt — việc nhỏ (~30 phút), không phải nhịp lớn. Không sửa VO/scenes JSON (VO đã sạch).
- (6) Thứ tự: R4∥R5 sau R3 là SAI cho R5 — video độc lập backend/docker, chạy ∥ R1/R2 được, không cần đợi smoke. R4 bắt buộc sau R3 (cần backend/docker khỏe + postgres sẵn). Ponytail cắt thêm: virtualized mặc định → conditional; 5 parser song song → spike tuần tự; M1L1 "điền số" → 1 call verify; không file mới cho smoke checklist (ghi WORKFLOW_STATE).
- Không tìm được plan đơn giản hơn ngoài 6 điểm trên: giữ 5 nhịp, giữ mirror market_store, giữ admin-only, giữ mp4 local-only.

## Current Status 8
- Phase 2 DONE (Scope 8 chốt). Verify DONE. Plan 8 candidate → debate DONE (REVISE minor 6 điểm: chấp nhận 5 nội dung + CHALLENGE điểm thứ tự — giữ ý user R4∥R5 sau R3, R5 sớm chỉ opportunistic khi chờ đợi). Plan 8 + Files 8 Approved (virtualized conditional, DELETE cuối, coverage HOSE+HNX, V2-1-call). Sẵn sàng implement R1→R2→R3→R4∥R5.

## Implementation Notes 8 (implementor 15-16/10/2026 — R1+R2+R4a+R4b+R5 DONE, R3 BLOCKED)
- R1 rates full (ingest.py +5 hàm seed-snapshot + hash-skip + `ingest_all_r1`; cached_adapter `_shape` nhận `updated_at` cho banks): unit 13 passed (mới `test_r1_minimums_all_groups_seed`: tối thiểu + hash-skip + get_rates 5 nhóm). Ingest thật `data/rates_store.db`: deposit 16 (4 NH×4 kỳ, seed:deposit_listed_2025-10) / lending 6 (3 NH, seed:lending_listed_2025-10) / avg 2 (2025-09, seed:sbv_avg_2025-09) / vnibor 6 kỳ (seed:vnibor_2025-10-14) / banks 5 (seed:banks_meta) / policy 3 giữ nguyên (fetch luatvietnam thật). Live WAF/DNS chặn (pattern Phase B/B1) → seed tính đạt theo debate, source ghi rõ. Không đổi schema 6 bảng.
- R2 Batch 2 (backend unit 18 passed = 14 cũ + 4 mới): storage `_ensure_extra_cols` (7 cột nullable session_id/user_id/version/env/cost/scores/tags, ALTER ADD COLUMN idempotent, không alembic) + comments table/methods + update_trace_meta + delete_trace; routes POST/GET comments + PATCH meta + DELETE admin-only; TraceSummary +7 optional (backward-compat, test null-default). Frontend: TracesTable selection checkbox + Xóa (confirm) + note virtualized-conditional; TraceDetailTabs TraceDag SVG nội bộ (<details>) + DeleteTraceButton (useRouter, confirm); FeedbackTab comments per node (span_id optional + Tải comments). tsc sạch, eslint traces 0 errors 0 warnings (fix no-location-assign → router.push).
- R3 smoke BLOCKED (môi trường, không phải code): `docker` không tồn tại trong shell này (where docker/pigman rỗng) → không chạy `docker compose up -d` được; cần người chạy + checklist Status 7. e2e 3/3 pass (TestClient, không cần server).
- R4a daily VN30 gate XANH live: `market_store/universe.py` (VN30_2025 30 mã snapshot rổ HSX 2025 + backfill_universe tái dùng ingest.backfill + backfill_intraday_pilot); chạy live 16 mã mới (14 mã trùng pilot 4a skip-meta) → VN30 30/30 OK (>400 rows/mã), tổng 58,960 rows, max_date 2026-10-15 (freshness T+1 so với hôm nay). R4b intraday pilot 5/5 (VCB/HPG/FPT/VNM/BID, mỗi 62 rows 2026-07-17→2026-10-15) — caveat: vnstock trả daily-resolution cho interval=1h (62 phiên/3 tháng), chưa phải nến giờ thật. R4c postgres + cron ngoài + HOSE/HNX full: CHƯA (cần backfill ngày + migration, để nhịp sau; compose postgres đã sẵn từ trước).
- R5 M1L1 DONE local: V2 budget_50_30_20(12tr) = 6.0/3.6/2.4tr khớp VO S3 (không sửa VO/JSON, V1 label giữ); TTS 8 scenes VO 121.5s; render --force `out/M1L1.mp4` 27.5MB; audio + mp4 trong out/ ignored (không push). V3 human-review chờ user.
- Gate: full unit **794 passed / 0 failed** (baseline 789 + 1 rates + 4 traces), e2e 3/3, tsc sạch, eslint traces sạch.

## Current Status 8 (tiếp — IMPLEMENT 15-16/10/2026)
- R1 DONE (6/6 nhóm đạt tối thiểu, get_rates verify 6 nhóm). R2 DONE (6 mục: nullable cols + comments + selection + DAG SVG + virtualized-conditional + DELETE cuối). R3 BLOCKED (no docker binary). R4a+b DONE (VN30 30/30 + intraday pilot 5/5, caveat resolution); R4c + HOSE/HNX full để sau. R5 DONE local (mp4 27.5MB, V3 chờ duyệt).
- Push nhịp sau khi reviewer duyệt (working tree đúng scope Plan 8: 11 modified + universe.py mới; artifacts cố ý để lại: report-gpt41.json, frontend.dev.log, trau-video audio).
- **PUSH DONE 16/10/2026:** `8c75304..fac5dd4 main -> main`, không force/amend — `8dc7e24` rates R1, `e82e6a2` traces Batch 2, `fac5dd4` pipeline R4a/b + WORKFLOW_STATE. Untracked còn lại để nguyên (artifact/log/audio-build).

## Next Agent
- reviewer (review R1+R2+R4a/b+R5: rates seed-snapshot + traces Batch2 + universe/intraday + M1L1 mp4 local; gate số bên trên; R3 smoke + R4c/HOSE-full + V3 là việc người/nhịp sau)

## Request mới (16/10/2026 — R3 smoke bằng docker trên WSL)
- User: tiếp tục với docker trên WSL (R3 smoke bị BLOCKED vì shell Windows không có binary docker).
- Planner đối chiếu thật 16/10: WSL có distro `Ubuntu-22.04` (đang Stopped, tự start khi gọi), trong WSL có `docker 29.7.2 + compose v5.5.0`, `docker.service` đang `activating (start)` — daemon có thể lên được. Compose `docker-compose.yml` (prod, 6 services, backend start_period 240s / mcp 180s) và `docker-compose.dev.yml` đều tồn tại.
- Smoke checklist kế thừa (Status 7/8): backend `/health` + login admin (`admin@finsight.vn`) + traces list (sort 4 cột/search hit-miss/date/pagination total/visibility persist/copy) + detail (5 tabs, waterfall expand/collapse, click span IO, truncated Badge, feedback POST/GET roundtrip) + rates `get_rates` + Batch 2 mới (comments/DELETE/DAG). e2e 3/3 đã pass không cần server.

## Open Questions (R3-docker — chờ user chốt trong chat)
- DONE 16/10/2026 — user trả lời 4/5: scope mở rộng (traces + rates + Batch 2 + M1L1), retry tối đa 2 lần (down + kill port + rebuild), down sạch sau smoke, lệnh không sudo. Còn lại (compose prod/dev) giao debate chọn tối ưu.

## Constraints (R3-docker)
- Planner: không sửa code ngoài WORKFLOW_STATE.md.
- Chạy trong WSL (`wsl -e sh -c ...`), workdir mount qua `/mnt/f/...` — build context lớn, lần đầu build image có thể lâu; không commit artifacts/log.
- Không force-push/amend-fail; kết quả smoke ghi WORKFLOW_STATE (pass/fail từng mục checklist).

## Current Status (R3-docker 16/10/2026 — planner kiểm tra môi trường, chưa plan)
- Windows: không có docker. WSL `Ubuntu-22.04`: docker 29.7.2 + compose v5.5.0 có sẵn; daemon đang activating (chưa verify `docker ps` OK). Tiền lệ: WSL dockerd restart ~10 phút (ghi ở Docker packaging) — cần retry.
- Chưa chốt: compose prod hay dev; scope smoke; timeout/retry tối đa; giữ stack hay down sau smoke.

## Clarified Scope R3-docker (chốt 16/10/2026 — 4/5 câu user + 1 giao debate)
- Diễn đạt lại: chạy smoke R3 bằng docker trên WSL theo đúng luật retry của user (dockerd restart → `compose down` + kill process chiếm port + rebuild, tối đa 2 lần), xong `down` sạch. Lệnh không sudo.
- Scope mở rộng (user chốt): traces list/detail + feedback (checklist Status 7/8) + rates `get_rates` 6 nhóm + Batch 2 (comments/DELETE/DAG) + M1L1 (verify file mp4 local, không render lại).
- Compose file (planner đề xuất tối ưu): prod `docker-compose.yml` — khớp gate all-green đã document (backend `/health` 200 + frontend `/api/health` 200, 6 services, start_period backend 240s/mcp 180s, admin defaults trong env). Debater quyết prod/dev.
- WSL wedge (verify thật 16/10): `docker --version` OK nhưng `docker ps` treo >60s (daemon activating + lỗi systemd user session) — implementor phải `wsl --shutdown` nếu kẹt + bounded-wait mọi lệnh docker (`timeout`, `DOCKER_CLIENT_TIMEOUT`/`COMPOSE_HTTP_TIMEOUT`), port Windows 3000/8000/8001/5432/6379/6333 đang free.

## Constraints R3-docker
- Planner: không sửa code ngoài WORKFLOW_STATE.md.
- Smoke-only: không sửa code sản phẩm trong nhịp này trừ khi debate cho phép fix nhỏ; bug tìm được → ghi report + để follow-up.
- Không commit secrets/DB/audio/out/log/images; `down` sạch sau smoke (user chốt); không force-push.
- Mọi lệnh docker có bound thời gian; retry tối đa 2 lần theo luật user.

## Acceptance Criteria R3-docker
1. Stack healthy: backend `/health` 200 + frontend `/api/health` 200 (`agent_ready:true`).
2. Login admin + checklist traces/feedback/rates/Batch2/M1L1 pass từng mục (ghi pass/fail vào WORKFLOW_STATE).
3. `compose down` sạch sau smoke; kết quả + hash/commit (nếu có) đã báo.

## Library verification R3-docker (16/10/2026 — planner verify trước Plan)
- Compose prod đọc thật (`docker-compose.yml:89-183`): backend port 8000, `alembic upgrade head` trước uvicorn, healthcheck curl `/health` start_period 240s; frontend port 3000, healthcheck wget `/api/health` start_period 40s; ADMIN_EMAIL/PASSWORD defaults `admin@finsight.vn/admin123`; volumes `app_data` share sqlite; qdrant không healthcheck (đúng tiền lệ).
- WSL đọc thật: `Ubuntu-22.04`, docker 29.7.2 + compose v5.5.0; `docker ps` treo >60s khi daemon activating — phải bounded-wait + shutdown-phục hồi.
- Port Windows đọc thật (`Get-NetTCPConnection` 16/10): 3000/8000/8001/5432/6379/6333 đều free — chưa cần kill, implementor re-check trước `up`.

## Plan R3-docker (Approved sau debate 16/10 — REVISE 5 điểm đã tiếp thu, xem Debate Notes R3-docker)
1. **Readiness WSL/docker (bounded, đủ recovery):** phân biệt daemon-chết vs socket-treo (`docker version --format` + `service docker status` bounded); nếu wedged → `wsl --shutdown` rồi bắt buộc `wsl -d Ubuntu-22.04 echo ok` mới retry `docker ps`; check không-sudo (`groups` có `docker`, `DOCKER_HOST` rỗng); port free 2 mặt (Windows `Get-NetTCPConnection` + WSL `ss -ltnp`) chỉ trước up + sau down; `timeout 25s` + tối đa 3 vòng. Export `DOCKER_CLIENT_TIMEOUT`/`COMPOSE_HTTP_TIMEOUT`.
2. **`compose up -d --build` prod `docker-compose.yml` (dev loại):** workdir WSL `/mnt/f/financial_insight_agent`; đợi healthy theo deadline (backend ≤6 phút sau start_period 240s, frontend sau backend healthy); fail → chỉ thu `docker ps` + `logs --tail 50` + health status.
3. **Triage retry đúng luật user (tối đa 2 lần):** infra-flake (dockerd restart/kẹt) → `compose down` + kill port 2 mặt + rebuild (retry 2 mới `--build` nếu image vừa build xong); app-bug (unhealthy do code/config) → DỪNG, ghi report WORKFLOW_STATE, để follow-up — không fix code nhịp này, không đốt rebuild.
4. **Smoke reorder (M1L1 pre-check, DELETE cuối):** M1L1 mp4 local pre-check trước `up` (fail-fast) → health infra → login admin → READ (traces list/detail, `get_rates` 6 nhóm, DAG) → WRITE (feedback/comments POST/GET) → DELETE CUỐI trên trace test-only riêng. Ghi pass/fail từng mục.
5. **`compose down` sạch (giữ volumes):** `down` không `-v`/`--rmi` + verify `docker ps` rỗng + port free + báo cáo + hash hiện tại.

## Files To Change R3-docker (Approved — smoke-only, giữ volumes)
- Sửa: không file code nào (app-bug → report + follow-up, không fix nhịp này).
- Ghi: `WORKFLOW_STATE.md` (pass/fail từng mục + `ps`/`logs --tail 50` khi fail + hash).
- Chốt: compose prod (dev loại); `down` không `-v`/`--rmi`; M1L1 verify file local.
- Không sửa: compose files, `.env` secrets, eval harness.

## Debate Notes R3-docker (16/10/2026 — Plan R3-docker, verdict REVISE, planner chấp nhận toàn bộ)
- (1) Chốt prod (khớp gate tiền lệ + healthcheck frontend; dev `npm run dev` không healthcheck → loại). Đúng đề xuất planner.
- (2) Recovery đủ: phân biệt daemon/sock + restart tường minh + check không-sudo + port 2 mặt. Chấp nhận.
- (3) Triage retry infra-flake vs app-bug (không đốt rebuild cho bug code). Chấp nhận.
- (4) Reorder: M1L1 pre-check + READ trước WRITE + DELETE cuối test-only. Chấp nhận.
- (5) Down giữ volumes + verify rỗng. Chấp nhận. Không điểm nào vô lý để challenge.

## Current Status R3-docker 2 (16/10/2026)
- Phase 2 DONE. Verify DONE. Plan candidate → debate DONE (REVISE 5 điểm ACCEPTED toàn bộ). Plan + Files Approved. Sẵn sàng implement smoke WSL.

## Next Agent
- implementor (Plan R3-docker Approved: readiness bounded → compose prod up → triage retry ≤2 → smoke reorder → down giữ volumes; ghi pass/fail WORKFLOW_STATE)

## Request mới (16/10/2026 — shadcn full sweep frontend, user chốt ở build mode)
- Nền shadcn đã có (components.json base-nova, TW4 tokens, 8 ui comps genuine, theme toggle chạy tốt, không CSS modules). Còn lại: native button×4 (TracesTable:290, TraceWaterfall:95+101, SpanIODetail:65), select×5 (TracesTable:186, FeedbackTab:74, DashboardControls:45+73, PriceChart:24), input/checkbox×~6 cùng các file, window.confirm×2/alert×1 (traces) → đổi sang shadcn; chưa có toast → thêm Sonner; Badge đã chuẩn ~10 files, còn status text rời (`(đang tải…)/(lỗi)/(mock)` ở PriceChart/PortfolioCard/PriceTable/SectorView) → Badge; border-t chia vùng → Separator (page.tsx:195+450, layout footer, header:95, ChatContainer:118+179, DashboardControls:40); loading rời rạc → Skeleton (ChartRenderer fallback, lần tải đầu dashboard, nút filter/login/signup loading, chat pending).
- User chốt (plan mode): full scope + Sonner + Skeleton/Separator/Badge.

## Clarified Scope 6 (16/10/2026)
- B1: `npx shadcn@latest add alert-dialog select checkbox sonner skeleton separator` (khớp components.json, không init lại; CLI tự kéo radix deps) + `<Toaster/>` vào layout qua wrapper đọc `.dark` class (giữ theme-toggle hiện tại, KHÔNG refactor next-themes).
- B2: thay native ở 5 file traces + DashboardControls/PriceChart/FeedbackTab; status text→Badge; border-t→Separator; Skeleton đúng chỗ loading; confirm/alert→AlertDialog+toast.
- B3: verify `tsc --noEmit` + `eslint` + `next build` sạch + check visual trang động chạm.
- Không đụng: theme toggle, charts libs, logic API. Đọc `node_modules/next/dist/docs` trước khi viết code (frontend AGENTS.md rule, Next 16).

## Acceptance Criteria 6
1. Không còn native button/select/input/checkbox ngoài `ui/`; không còn `window.confirm/alert`.
2. `<Toaster/>` mounted; toast thay alert; AlertDialog cho confirm xóa.
3. Skeleton đúng chỗ loading; Separator/Badge đúng chỗ chia vùng/status.
4. `tsc --noEmit` + `eslint` + `next build` sạch.

## Current Status 6
- Plan DONE 16/10/2026 (build mode). Chờ implementor chạy B1→B3.
- **IMPLEMENT DONE 16/10/2026** — đủ B1→B3, không thêm dep ngoài scope (radix/sonner đã có từ npm trước trong cây làm việc).
- **B1:** Deps + components đã tồn tại trong cây (`@radix-ui/react-alert-dialog|checkbox|select|separator` + `sonner` trong package.json; 6 files ui/ genuine shadcn khớp `components.json` style base-nova/TW4/cssVariables/lucide + mẫu `button.tsx`) → không chạy lại CLI init. Còn thiếu duy nhất `<Toaster/>` → đã mount trong `src/app/layout.tsx` (import trực tiếp `ui/sonner` — Server Component render Client Component, đúng Next 16 docs `05-server-and-client-components`; wrapper đọc `.dark` class sẵn có, giữ nguyên theme-toggle, không next-themes). Đọc trước khi code: `node_modules/next/dist/docs/index.md` + `01-app/.../upgrading/version-16.md` (proxy.ts đã đúng, async `params` ở traces/[id] đã `await` — không đụng) + `.../16-proxy.md` + `.../05-server-and-client-components.md`.
- **B2 — files đổi (20 sửa, logic/handler giữ nguyên, chỉ đổi element):**
  - `TracesTable.tsx`: select status→Select (sentinel `all`↔`""` vì Radix Item cấm value rỗng); checkbox cột + select-all + row→Checkbox (`onCheckedChange`, `v === true` cho TS); copy trace button→Button ghost; `window.confirm`→AlertDialog (state `confirmOpen` + `doDeleteSelected` tách từ handler inline); loading→5 Skeleton rows (`colSpan=cols+1`, empty-state chỉ khi `!loading`).
  - `TraceWaterfall.tsx`: 2 buttons→Button ghost (giữ aria-label, layout `h-4 w-4 p-0` / `justify-start font-mono text-xs` qua tailwind-merge).
  - `SpanIODetail.tsx`: copy span button→Button ghost (giữ `e.preventDefault()` trong `<summary>`).
  - `TraceDetailTabs.tsx`: confirm→AlertDialog; `window.alert`→`toast.error`, success thêm `toast.success` (từ `sonner`).
  - `FeedbackTab.tsx`: select điểm→Select; inputs comment/cSpan/cText→Input.
  - `DashboardControls.tsx`: 2 selects→Select, input ticker→Input; `border-t`→Separator đầu block.
  - `PriceChart.tsx`: select ticker→Select; status text suffix (2 chỗ PriceChart+RSIChart)→`DataSourceBadge` (Badge loading/error/live/mock).
  - `PortfolioCard.tsx`/`PriceTable.tsx`/`SectorView.tsx`: status text→Badge; lần tải đầu (`loading && !data`)→Skeleton cards/rows.
  - `ChartRenderer.tsx`: loading fallback heatmap/treemap `<p>`→Skeleton `h-[380px]`.
  - `MessageBubble.tsx`: assistant pending rỗng (`isStreaming && !content`, hook đã tạo message rỗng chờ token)→2 Skeleton lines; input chat giữ `ui/textarea`.
  - `login/signup`: submit loading text→Skeleton trong Button (giữ disabled).
  - Separator thay `border-t`: `page.tsx:195` (sparkline) + `:450` (FAQ) + `layout.tsx` footer + `header.tsx:95` (mobile nav, bọc fragment) + `ChatContainer.tsx:118` (input area). **Giữ nguyên** `ChatContainer.tsx:179` aside (`border-t lg:border-t-0 lg:border-l` responsive 2 trục — 1 Separator không biểu diễn được, 2 Separator tốn code vô ích).
  - Không đụng: theme toggle, charts libs, logic API/auth gate/server shells, `traces/[id]/page.tsx` async params.
- **B3 — Verify:** `tsc --noEmit` sạch; `eslint` 18 files touched **0 errors 0 warnings** (lần 1 timeout lạnh 240s + retry 600s mới xong — ghi nhận cho reviewer: cold-start eslint chậm, không phải treo); `next build` (Turbopack) sạch 9/9 routes. Grep: 0 `window.confirm/alert`; native `<select|input|button|textarea` chỉ còn trong `ui/` primitives.
- KHÔNG commit/push (user chưa yêu cầu). Untracked mới: 6 files `ui/` (đã có sẵn trước batch này) — stage cùng nhịp commit sau theo luật thematic (không `add -A`).
- **PUSH DONE 16/10/2026:** commit `7a5f18d` `feat(ui): shadcn full sweep + sonner/skeleton/separator/badge` — 27 files (+1849/-262: 6 ui mới + 14 sửa element + layout/toaster + package.json/lock + WORKFLOW_STATE). `43d97db..7a5f18d main -> main`, không force/amend. Review trước push: staged đúng scope (không `add -A`); cached diff scan sạch secret (chỉ match code template `Bearer ${token}` + key `sk-${i}`); bỏ lại: report-gpt41.json, frontend.dev.log, trau-video audio (đúng convention artifact local-only).

## Next Agent
- reviewer (review shadcn sweep B1→B3: element swap + Toaster + Skeleton/Badge/Separator + gate tsc/eslint/build bên trên; visual check các trang động chạm khi có môi trường chạy)

## Debate Notes R3-docker (16/10/2026 — Plan R3-docker, verdict REVISE)
- Đã đọc: Request mới R3-docker, Clarified Scope R3-docker, Constraints R3-docker, Acceptance Criteria R3-docker, Library verification R3-docker, Plan R3-docker candidate, Files To Change R3-docker, Current Status R3-docker 2 + đọc thật `docker-compose.yml` (prod: backend/mcp target production, frontend build + healthcheck `/api/health` start_period 40s, gates backend healthy) vs `docker-compose.dev.yml` (dev: target development + bind-mount `./src`, frontend `node:20-alpine npm install && npm run dev`, KHÔNG healthcheck frontend).
- (1) prod vs dev: chốt PROD. Vì: khớp gate all-green đã document (backend `/health` 200 + frontend `/api/health` 200 `agent_ready:true`); dev frontend không healthcheck + `npm install` mỗi `up` = chậm/khó đoán, không đo được Acceptance #1. Admin seed giống nhau cả 2 file (`admin@finsight.vn/admin123`) nên không phải tiêu chí phân biệt. Build prod lần đầu lâu hơn nhưng images giữ lại cho retry (không `--rmi`), ổn định hơn cho smoke. Dev chỉ dùng khi cần live-mount code — không phải mục đích smoke.
- (2) bounded-wait/wsl-shutdown CHƯA ĐỦ gỡ wedge: plan thiếu (a) phân biệt client-vs-daemon (`docker version` OK ≠ `docker ps` OK; thêm `docker version --format` + `systemctl is-active docker`/`service docker status` bounded để biết daemon chết hay socket treo); (b) lệnh restart tường minh sau `wsl --shutdown` (phải `wsl -d Ubuntu-22.04 echo ok` rồi mới retry `docker ps`, không retry mù); (c) kiểm tra không-sudo: `groups` có `docker` không + `echo $DOCKER_HOST` rỗng (nếu DOCKER_HOST trỏ sai hoặc thiếu group thì `docker ps` fail kiểu khác, shutdown không cứu được); (d) port-kill 2 mặt (Windows `Get-NetTCPConnection` + WSL `ss -ltnp`) vì stack map port qua cả 2. Giữ `timeout 25s` + `DOCKER_CLIENT_TIMEOUT`/`COMPOSE_HTTP_TIMEOUT` + tối đa 3 vòng đợi daemon (~3 phút).
- (3) smoke-only ĐÚNG hướng nhưng thiếu triage: phải phân biệt infra-flake (dockerd restart/kẹt → được retry đúng luật user tối đa 2 lần: `down` + kill port + rebuild) vs app-bug (container unhealthy do code/config → DỪNG, thu `ps` + `logs --tail 50` + health status, ghi report vào WORKFLOW_STATE, KHÔNG đốt retry rebuild vô ích). Không sửa code sản phẩm trong nhịp này; allowlist duy nhất là fix config-nhỏ kiểu env/healthcheck typo NẾU debate bổ sung sau — mặc định là không fix, để follow-up.
- (4) thứ tự smoke chưa tối ưu + thiếu guard destructive: M1L1 là check local (file `out/M1L1.mp4` tồn tại, không cần stack) → làm PRE-CHECK trước `up` để fail-fast. Sau `up`: health infra (backend/frontend/mcp/qdrant/postgres/redis) → login admin → READ-ONLY (traces list/detail, `get_rates` 6 nhóm, DAG render) → WRITE (feedback POST/GET, comments POST/GET) → DELETE CUỐI CÙNG trên trace test-only (tạo riêng/mượn trace rác, KHÔNG xóa data thật). Plan hiện gộp chung, rủi ro xóa trước khi đọc xong.
- (5) `down` giữ volumes là ĐÚNG với ý user "down sạch": sạch = hết containers/networks + port free, GIỮ volumes (`app_data/postgres_storage/qdrant_storage/redis_storage`) + images (không `down -v`, không `--rmi`) để không mất data/không rebuild lại từ đầu. Cần verify sau down (`docker ps` rỗng + port free) thay vì chỉ gọi lệnh.
- Ponytail cắt: (a) không render lại M1L1 (giữ verify file — plan đã đúng, giữ); (b) log khi fail chỉ `ps` + `logs --tail 50` + health, không dump full; (c) port check 2 lần (trước up + sau down), không check mỗi vòng retry; (d) retry 1 `up -d` không `--build` nếu image vừa build xong (chỉ rebuild khi image stale/đổi Dockerfile), retry 2 mới `--build` — vẫn trong luật "rebuild" của user nhưng rẻ hơn (user chốt rebuild nên không bỏ hẳn, chỉ xếp lại).

## Current Status R3-docker 3 (16/10/2026 — debate xong, chờ implement)
- Debate DONE 16/10/2026 — verdict REVISE (xem Debate Notes R3-docker). Plan candidate chưa implement được as-is; implementor sửa 5 điểm rồi chạy: chốt prod, bổ sung WSL recovery (restart tường minh + group/DOCKER_HOST + client-vs-daemon + port 2 mặt), triage infra-flake vs app-bug (retry chỉ cho infra), reorder smoke (M1L1 pre-check → health → login → read → write → DELETE test-only cuối), `down` giữ volumes + verify rỗng/port free.
- Scope/Constraints/Acceptance R3-docker giữ nguyên; Files To Change giữ smoke-only (chỉ ghi WORKFLOW_STATE.md).

## Implementation Notes R3-docker (implementor 16-17/10/2026 — SMOKE BLOCKED ở Readiness, không tới được `up`)
- M1L1 pre-check PASS trước `up` (fail-fast đúng plan): `frontend/trau-video/out/M1L1.mp4` tồn tại local, 27.5MB (27530184 bytes), 15/10/2026 — không render lại.
- Windows ports free 2 mặt (lúc check): `Get-NetTCPConnection` 3000/8000/8001/5432/6379/6333 đều free. Không-sudo OK (`groups` có `docker`, `DOCKER_HOST` rỗng).
- Daemon KHÔNG BAO GIỜ stable (readiness vượt bound 25s×3 vòng + retry): `docker ps`/`docker version`/`ss -lx` treo mọi lần (kể cả `timeout -s KILL`, `DOCKER_CLIENT_TIMEOUT=20`); probe python chứng minh socket connect OK nhưng `GET /_ping` timeout 8s — daemon nhận connect, không trả lời API.
- Root cause (journalctl đọc thật): **WSL VM reboot chu kỳ ~2 phút** — 12+ Boot IDs trong 00:55→01:29 (00:55, 01:00, 01:02, 01:06, 01:07, 01:09, 01:11, 01:13, 01:15, 01:16, 01:21, 01:23, 01:26, ~01:28; `uptime` lúc 01:29:16 = up 1 min). Mỗi boot dockerd (VD PID 686→733→726) nhận SIGTERM khi đang `Loading containers`, không bao giờ tới `active (running)`. Reboot có từ trước khi implementor chạm vào (00:55) → không phải do `wsl --shutdown` 1 lần của implementor.
- Nhiễu thêm: dockerd WSL đang restore stacks của người khác (`netflix-movie-recommendation-system_*`, `chatdev_*`, `compose-paddleocr-1` — sbJoin trong log) + docker-proxy giữ 6333/6334/8000/8001/6400 phía WSL (8000/8001 trùng backend/mcp của mình — nguy cơ port-conflict khi daemon hồi phục; KHÔNG kill vì không phải process của mình).
- Quyết định theo Plan bước 3 (triage): DỪNG ở Readiness, KHÔNG `compose up --build` — VM reboot/2phút thì build sẽ chết giữa chừng + rủi ro corrupt overlay state của stacks người khác. Retry-budget (≤2) không đốt vì cần daemon stable trước đã. Không sửa file code nào (đúng smoke-only).
- Tool-note: mỗi bash call chỉ 1 lệnh `wsl -d` (2+ lệnh wsl trong cùng 1 powershell invocation → ChildProcess.kill lặp lại 3 lần, đã verify pattern); `Start-Sleep` dài trong cùng lệnh cũng tăng rủi ro kill — sleep giữa các call thay vì trong call.

## Current Status R3-docker 4 (17/10/2026 — BLOCKED hạ tầng, cần người)
- R3 smoke CHƯA CHẠY (0/5 bước plan qua Readiness). Blocker: WSL `Ubuntu-22.04` reboot chu kỳ ~2 phút → dockerd không bao giờ ready → không `docker ps`/`compose up` được. Cần người kiểm tra host (RAM/host-process kill WSL? `.wslconfig` memory limit? task khác chiếm WSL?) rồi báo implementor chạy lại từ Readiness.
- Pre-checks đã PASS (giữ hiệu lực khi retry): M1L1 mp4 local OK; Windows ports free; no-sudo/DOCKER_HOST OK.
- Khi retry: check `uptime -p` >10 min trước mới `up`; `docker ps` trước để xem stacks lạ còn giữ 8000/8001 không; giữ nguyên Plan R3-docker (prod + triage + reorder + down giữ volumes).

## Next Agent R3-docker
- user/host-fix trước (dứt reboot cycle WSL), sau đó implementor retry smoke R3-docker từ Readiness theo Plan đã Approved (không cần debate lại)

## Request mới (17/10/2026 — smoke local Windows, bỏ WSL)
- User: chạy bằng pnpm + uvicorn thông thường trên Windows, không cần WSL nữa; kiểm tra còn việc nào không thì làm nốt.
- Planner verify thật 17/10: shell python có fastapi + torch 2.11.0+cpu (chạy uvicorn trực tiếp được); node v24.14.0 + pnpm sẵn; `frontend/node_modules` đã có (npm), `package-lock.json` có, `pnpm-lock.yaml` chưa có; port 3000/8000 free.
- Việc còn lại theo file: R3 smoke (treo vì WSL) + R4c (postgres + cron + HOSE/HNX full) + R5 V3 (user duyệt) + reviewer A→B3/R1R2R4/R5 + lặt vặt (test stale name, purge approx).

## Answered (local-smoke — user chốt 17/10)
- Q1: LOCAL trước, **sau đó WSL docker sau** (docker-fix r2 đã chốt — implement sau khi local smoke xong).
- Q2: OK lệnh chạy (MCP + backend + frontend). **Cần cài redis** (không degrade).
- Q3: chọn (b) — sau smoke: reviewer các batch treo (shadcn A→B3, R1R2R4/R5) + lặt vặt (M3L2 điền số, test stale name, purge approx). KHÔNG làm R4c nhịp này.
- Q4: kill sạch process sau smoke.
- Q5: chỉ `pnpm dev` — không `pnpm install`, không sinh/track lock mới.
- Bổ sung: `.venv` project hỏng hoàn toàn → **xoá + tạo lại `.venv` mới** (user yêu cầu), dùng cho smoke.

## Verify bổ sung trước plan (17/10)
- Extra-index `https://vnstocks.com/api/simple` có đủ: vnstock (4.0.8/4.0.9), vnai (2.6.2/2.6.3) → `pip install -e .` resolve OK (PyPI đã quarantine cả 2).
- Redis: winget chỉ có bản 3.0.504 (quá cũ, loại); choco có redis-64/memurai nhưng shell **non-admin** → không cài service; chọn portable: **redis-windows/redis-windows 8.10.2** asset `Redis-8.10.2-Windows-x64-msys2.zip`, SHA256 công bố `7C8CEBD50347EAA1D9E784DA842ED47A4F33394637835531D6614777B950EE85`. Compose dùng redis:7-alpine → 8.10.2 tương thích ngược.
- Routes API: auth/memory/traces/rag/market (app.py:552-556). Chat = frontend `/api/ask-stream` (SSE). traces: list GET /traces, detail GET /traces/{id}, feedback POST/GET, comments POST/GET, meta PATCH, DELETE. `get_rates` = MCP tool `src/mcp_server/tools/rates.py:26`.
- Data local sẵn sàng cho smoke: `data/traces/traces.db` 2.5MB (+wal/shm), `rates_store.db` 78KB, `market_store.db` 9.9MB, `app.db` 16KB, `qdrant_local*`, `rag/registry.db`.
- `.venv` mới sẽ cho `interfaces`/`mcp_server` importable mọi nơi (editable `pip install -e .`, hatch `packages=["src"]`) — không cần `--app-dir`/`PYTHONPATH` nữa.

## Plan (local-smoke r2 — 17/10, sau debate; 4 điểm bắt buộc + 4 optional đã áp)
- L1 Env prep:
  a) Pre-check: port 3000/8000/8001/6379 free; `frontend/trau-video/out/M1L1.mp4` tồn tại (27.5MB, fail-fast).
  b) Venv: `Remove-Item -Recurse -Force .venv` (.gitignore dòng 30 ignore `.venv/`) → `F:\miniconda3\python.exe -m venv .venv` → `.venv\Scripts\python.exe -m pip install -U pip` → `.venv\Scripts\python.exe -m pip install -e ".[dev]" --extra-index-url https://vnstocks.com/api/simple` — **BẮT BUỘC truyền `timeout` ≥1,800,000 ms** (mặc định 2 phút của tool sẽ giết giữa chừng); ưu tiên chạy detached theo cơ chế L2-PROC (Start-Process + 2 log `.out`/`.err`) + poll; log `%TEMP%\opencode\venv-install.log`; pip cache giúp retry rẻ. `[dev]` GIỮ (pytest cho reviewer batch sau). Verify: `pip show financial_insight_agent` (editable); import `interfaces.api.app` + `mcp_server.server` + `vnstock` + `redis` (đo thời gian; cold ~2.5–3 phút).
  c) Redis portable (non-admin): tải `https://github.com/zkteco-home/redis-windows/releases/download/8.10.2/Redis-8.10.2-Windows-x64-msys2.zip` → **verify SHA256 = `7C8CEBD5…EE85`** (chỉ bản chính; fallback không công bố hash) → giải nén `%LOCALAPPDATA%\redis\8.10.2\` → start `redis-server.exe --port 6379 --bind 127.0.0.1 --save "" --appendonly no --dir %LOCALAPPDATA%\redis\data` (PowerShell có thể bỏ arg rỗng `--save ""` — vô hại vì `--appendonly no`) → `redis-cli ping` = PONG. Fallback nếu exe lỗi (DLL msys2): tporadowski 5.0.14.1 zip (không verify hash).
- L2-PROC (cơ chế process nền — điều kiện để MCP+backend+frontend sống đồng thời): mỗi server start bằng `Start-Process -PassThru` detached, **log 2 file `.out`/`.err` riêng** (cùng 1 file → lỗi ngay), ghi PID ngay khi start; KHÔNG `Start-Sleep` dài trong cùng call (bị tool kill) — poll readiness bằng các call ngắn riêng.
- L2 Smoke (python qua `.venv\Scripts\python.exe`; thứ tự MCP → backend → frontend):
  a) MCP 8001: `-m mcp_server.server --transport streamable-http --host 0.0.0.0 --port 8001` (workdir root) — process sống + port listen.
  b) Backend 8000: `-m uvicorn interfaces.api.app:app --port 8000` — đợi `/health` 200, deadline ≤6 phút (cold import + lifespan init_db/seed admin app.py:162-177).
  c) Frontend 3000: `pnpm dev` (cwd frontend/) — đợi `http://localhost:3000/api/health` 200 `agent_ready:true` (deadline ≤3 phút).
  d) API smoke (Invoke-RestMethod; login path thật **`/api/v1/auth/login`**, prefix `/api/v1` app.py:552): login admin (`admin@finsight.vn`/`admin123`) → JWT → READ: traces list (sort/search/date/pagination) + detail 1 trace + `get_rates` 6 nhóm (MCP tool `rates.py:26` — client `mcp` trong .venv hoặc import hàm; rates_store 6/6 nhóm có data).
  e) Trace cô lập (an toàn — KHÔNG đụng 489 trace thật): tạo trace tổng hợp `TraceStore("data/traces/traces.db")` + `Tracer(store=...).start_span("smoke-test-<ts>")` (tạo trace_id mới) → mọi WRITE **chỉ trên `smoke-test-*`**: comments POST→GET + feedback POST→GET + meta PATCH. Thử chat 1 lần bounded qua UI `/api/ask-stream` là optional (bonus). **Không tạo được trace cô lập → BỎ HẲN DELETE** + ghi "DELETE = SKIPPED (no isolated trace)".
  f) UI smoke best-effort cùng session (chrome-devtools `http://localhost:3000`): login → traces list toolbar → detail tabs/waterfall → comments → DELETE confirm. Không làm được → ghi "UI chưa verify mắt", không chặn.
  g) DELETE cuối: xoá DUY NHẤT trace `smoke-test-*` vừa tạo (API DELETE `/api/v1/traces/{id}`). Ghi pass/fail từng mục.
- L3 Kill & cleanup (user chốt): kill theo PID đã ghi + **fallback port-owner** `Get-NetTCPConnection -State Listen -LocalPort <p> | Stop-Process -Force` (và/hoặc `taskkill /T /F /PID` cho process con `pnpm dev`/uvicorn workers); redis: `<redis>\redis-cli.exe shutdown nosave` → fallback kill PID; verify 4 port free sau kill. Không xoá `.venv`/redis (chỉ stop process).
- L4 Ghi WORKFLOW_STATE: bảng pass/fail + PID/log + lệnh restart (cho lần sau). KHÔNG commit/push (merge v1.2 vẫn chờ user; không file code nào đổi). Note: `.env QDRANT_PATH=./data/qdrant_local` (không phải `_v117`); RAG/`search_knowledge` không thuộc smoke.

## Files To Change (local-smoke)
- Create: `.venv/` (recreate, gitignored), `%LOCALAPPDATA%\redis\8.10.2\` + `%LOCALAPPDATA%\redis\data\` (ngoài repo).
- Update: `WORKFLOW_STATE.md`.
- Không đụng: code `src/`, `frontend/`, `.env`, docker files, 26 scenes untracked (merge v1.2), `frontend/node_modules`, lockfiles.

## Acceptance Criteria (local-smoke)
1. `.venv` mới tạo; `pip install -e ".[dev]"` (extra-index) thành công; import app/mcp/vnstock từ `.venv` OK.
2. Redis portable chạy (SHA256 zip khớp) + `PING`=PONG.
3. Backend `/health` 200 + frontend `/api/health` 200 (`agent_ready:true`) trong deadline.
4. Checklist smoke ghi pass/fail rõ (login/READ traces+rates+DAG/WRITE comments+feedback+meta/DELETE test-only/M1L1 pre-check/UI best-effort).
5. Kill sạch sau smoke: 4 port free, không process sót; WORKFLOW_STATE cập nhật; không commit/push.

## Constraints (local-smoke)
- Planner: không sửa code ngoài WORKFLOW_STATE.md.
- Nhịp này: local Windows (uvicorn + pnpm dev), KHÔNG đụng WSL/docker trong nhịp này; docker-fix r2 implement SAU khi local smoke xong (user chốt thứ tự).
- `.venv` xoá + tạo lại (user yêu cầu); redis cài portable non-admin (không service); chỉ `pnpm dev` (không `pnpm install`, không sinh lock mới).
- Không commit secrets/DB/audio/out/log/node_modules (+ pnpm-lock mới nếu sinh ra thì hỏi user trước khi track); không force-push.
- Kết quả smoke + việc làm nốt ghi WORKFLOW_STATE.

## Current Status (local-smoke — plan r2 chốt 17/10, chờ implement)
- Debate DONE — verdict REVISE (4 bắt buộc + 4 optional) đã áp TOÀN BỘ vào plan r2 (trace cô lập `smoke-test-*` + bỏ DELETE nếu không tạo được; L2-PROC detached 2 log; kill port-owner fallback; timeout pip ≥1.8M ms; login `/api/v1/auth/login`; .gitignore dòng 30; URL redis zkteco-home; bỏ "DAG data" dư). Không có điểm nào cần challenge — debater verify bằng chứng đầy đủ.
- Plan + Files + AC sẵn sàng; chờ implementor.

## Next Agent (local-smoke)
- implementor: chạy Plan local-smoke r2 L1→L4 (recreate `.venv` + pip `timeout ≥1.8M ms`/detached → redis portable 8.10.2 verify SHA256 → MCP 8001/backend 8000/frontend 3000 theo L2-PROC → API smoke `/api/v1` + trace cô lập `smoke-test-*` → UI best-effort → kill PID+port-owner → ghi pass/fail + PID/log vào WORKFLOW_STATE). KHÔNG đụng merge v1.2 (26 scene untracked + 3 M), không commit/push, không lẫn docker-fix.

## Debate Notes (local-smoke — debater, 17/10/2026)
**VERDICT: REVISE** (hướng đúng — KHÔNG viết lại; 4 điểm bắt buộc + 4 optional). Đã tự verify rẻ: đọc `.venv`/`pyproject.toml`/`routes/auth.py`/`routes/traces.py`/`app.py`/`agent.py`/`storage.py`/`tracer.py`/`vector_store.py`/`.env`(tên key)/`frontend/package.json` + đếm row sqlite + test thật background-process + websearch redis-windows.

**Đã verify độc lập (bằng chứng):**
- `.venv` hiện tại hỏng đúng phần cốt lõi: `python --version`=3.13.2 chạy, `redis`/`vnstock` import OK, nhưng `import interfaces.api.app` → `ModuleNotFoundError: No module named 'interfaces'` (editable install chết) + warning `Could not find platform independent libraries <prefix>`. → recreate là đúng, không phí (dù không "hỏng hoàn toàn" như chữ user).
- `pyproject.toml`: `[dev]` extras = pytest/black/ruff/mypy/pre-commit/httpx/reportlab (nhỏ, pure-python, KHÔNG kéo torch). `uvicorn`/`fastapi`/`redis>=5.0.0` ở deps chính.
- DB local: `traces.db` = **489 traces / 3387 spans / 0 feedback** (data THẬT, `data/` gitignored → xoá KHÔNG recover được); `rates_store.db` = 6/6 nhóm có data (policy 3, deposit 16, lending 6, avg 2, vnibor 6, banks 5) → `get_rates` 6 nhóm sẽ có số.
- Backend KHÔNG cần postgres: `.env` `DATABASE_URL=sqlite+aiosqlite:///./data/app.db` (config default sqlite local; docker mới override) → plan bỏ postgres là ĐÚNG.
- `.env` đủ `NVIDIA_API_KEY/2/3` + `REDIS_HOST/PORT` + `ADMIN_EMAIL/PASSWORD`; `frontend/package.json` có `"dev": "next dev"`, `next@16.3.4`, `node_modules/.bin/next` tồn tại, **`pnpm-lock.yaml` KHÔNG tồn tại** (khớp "chỉ pnpm dev, không sinh lock").
- API path thật: auth = **`/api/v1/auth/login`** (prefix `/api/v1` ở app.py:552; `/login` ở auth.py:88 — line 50 là `/register`); traces = `/api/v1/traces...`; routes đủ GET list/detail, POST/GET feedback, POST/GET comments, PATCH meta, DELETE.
- Harness thật: `Start-Process` detached **sống xuyên bash call** (đã chạy `python -m http.server 6399`, call sau còn listen, PID khớp) → L2 khả thi. NHƯNG: (i) `Start-Process` redirect stdout+stderr CÙNG 1 file → **lỗi ngay**; (ii) lệnh chứa `Start-Sleep` dài cùng call → `ChildProcess.kill` (tái hiện được).
- Redis: repo build thật = `zkteco-home/redis-windows` (release "Redis 8.10.2 Stable for Windows"), asset **`Redis-8.10.2-Windows-x64-msys2.zip`**; pattern hash-per-release khớp (8.10.1 msys2 công bố `4E8F2F95…607A`, cùng định dạng hash planner đưa). redis-py 8.1.0 (đã cài) tương thích Redis server 5–8.

**ĐIỂM BẮT BUỘC SỬA (đủ để REVISE):**
1. **An toàn trace test-only — rủi ro mất data thật (nặng nhất).** Fallback "mượn trace cũ nhỏ nhất + DELETE" KHÔNG an toàn: 489 traces là data thật, `data/` gitignored nên mất là vĩnh viễn; WRITE (comments/feedback/meta) trên trace mượn cũng bẩn data thật. Sửa: tạo **trace tổng hợp cô lập** bằng API có sẵn thay vì mượn — `TraceStore("data/traces/traces.db")` + `Tracer(store=...).start_span("smoke-test-<ts>", kind=...)` (verified: `start_span`/`begin_span` → `_upsert_trace` tạo trace_id mới). Mọi WRITE + DELETE chỉ trên trace `smoke-test-*`. Thử chat 1 lần (bounded) để smoke đường thật là optional; **nếu KHÔNG tạo được trace test-only → BỎ HẲN DELETE** (tuyệt đối không xoá trace thật) + ghi "DELETE = SKIPPED (no isolated trace)".
2. **Cơ chế process nền phải ghi rõ (L2 fail nếu không).** Start mỗi server `Start-Process -PassThru` detached, log **2 file `.out`/`.err` riêng** (cùng file = lỗi), ghi PID ngay, return (KHÔNG `Start-Sleep` dài trong cùng call); poll readiness bằng call ngắn riêng. Đây là điều kiện để MCP+backend+frontend sống đồng thời cho API/UI smoke.
3. **L3 kill phải xử lý process con / port owner.** Kill theo PID đã ghi chưa đủ cho `pnpm dev` (next dev có thể là process con) và uvicorn workers. Thêm fallback `Get-NetTCPConnection -State Listen -LocalPort <p> | Stop-Process -Id $_.OwningProcess -Force` (và/hoặc `taskkill /T /F /PID`); verify 4 port free SAU khi kill. Redis: ưu tiên `<redis>\redis-cli.exe shutdown nosave` (graceful; đã `--save ""` nên không mất gì) rồi verify port, fallback kill PID.
4. **pip install dài + rủi ro harness kill.** BẮT BUỘC truyền `timeout` tường minh (≥1,800,000 ms) cho call cài (mặc định 2 phút sẽ giết giữa chừng); tốt hơn: chạy pip detached + log + poll (đồng cơ chế #2) để tool-hiccup không giết. pip cache dùng lại → retry rẻ. **`[dev]` GIỮ** (nhỏ; reviewer batch sau cần pytest).

**OPTIONAL (nên sửa, không chặn):**
5. Ghi đường login chính xác `/api/v1/auth/login` (plan ghi "discover từ auth.py:50" — line 50 là `/register`, `/login` ở line 88-89).
6. `.gitignore` ignore `.venv` ở **dòng 30** (plan ghi dòng 10) — sửa số cho đúng.
7. Redis: ghi URL tải cụ thể (asset `Redis-8.10.2-Windows-x64-msys2.zip` từ release `zkteco-home/redis-windows` 8.10.2); nếu verify SHA256 bản chính thì nên verify cả hash fallback tporadowski (hoặc ghi rõ chỉ verify bản chính). Lưu ý PowerShell có thể bỏ arg rỗng `--save ""` — vô hại vì `--appendonly no` đã tắt persist.
8. "DAG data" dư (nằm trong trace detail, không có API DAG riêng) → có thể bỏ khỏi checklist; thêm 1 dòng note: `.env QDRANT_PATH=./data/qdrant_local` (KHÔNG phải `_v117`) — RAG/`search_knowledge` KHÔNG thuộc smoke nên không chặn, chỉ note nếu vô tình chạm.

**KHÔNG đổi (đúng, giữ nguyên):** recreate `.venv` + redis portable + kill sạch (user yêu cầu); bỏ postgres (đúng vì sqlite); không đụng merge v1.2 (26 scene untracked + 3 M) / docker-fix / không commit-push; giữ UI best-effort (chrome-devtools có sẵn) nhưng phụ thuộc điểm #2.

**PONYTAIL CẮT:** giữ `[dev]` (đừng cắt — reviewer cần); KHÔNG cắt redis/kill/recreate (user yêu cầu); giữ fallback redis (rủi ro DLL msys2 là thật); bỏ "DAG data" dư; gộp writes+delete quanh 1 trace tổng hợp (ít thao tác + an toàn hơn mượn trace thật).

## Fix GLM max_steps (17/10/2026 — DONE, ngoài scope project)
- User báo OpenCode + GLM 5.3 Flash lỗi `unknown_parameter: json: unknown field "max_steps"`.
- Root cause: 8 file agent global `C:\Users\DELL\.config\opencode\agents\*.md` có frontmatter `max_steps: N` (planner 8, implementor 12, tester 6, linter 4, security-reviewer 6, reviewer 5, debater 4, commit-message 3). Frontmatter agent OpenCode không nhận field này → bị route vào `options` → nằm trong request body gửi provider; GLM validate strict nên chặn (provider khác ignore field lạ).
- Fix: xoá `max_steps` cả 8 file (grep verify sạch). Các cap này chưa từng hoạt động thật → không mất hành vi. Field đúng nếu muốn cap thật: `steps` (không thêm — YAGNI).
- User cần QUIT hẳn OpenCode + mở lại (config load 1 lần lúc start) — áp dụng cho CẢ 2 fix dưới đây.
- Fix 2 (17/10, phát hiện khi spawn debater): `Model not found: opencode/muse-spark-1.3-contributor-free` — zen đã gỡ model này khỏi registry (còn: beam-free, deepseek-v4.1-flash-free, glm-5.3-flash-free). Đã đổi `model:` cả 8 file agent sang `opencode/deepseek-v4.1-flash-free` (model session hiện tại, đang chạy verified). Muốn agent chạy GLM 5.3 Flash: thay lại 1 dòng `model:` trong 8 file.

## Request mới (17/10/2026 — gộp dữ liệu bài học v1.2 vào bộ cũ)
- User bổ sung dữ liệu bài học + cảnh mới ở `frontend/trau-video` (video_scenes/, xu-video/) và `data/lessons` (new_lessons_v1_2/); yêu cầu gộp với bộ cũ cho thống nhất rồi xoá các phần mới thêm.

## Khảo sát thật (planner 17/10 — số liệu verified)
- `public/lessons/` (canonical, tracked trong git, pipeline đọc): 30 bài M1L1–M8L3, index count=30, nhân vật "Trâu Tí".
- `video_scenes/` (untracked mới): 56 bài = 30 cũ + 26 mới (M1L5-7, M2L5, M3L6-7, M4L5, M6L4, M8L4-10, M9L1-5, M10L1-6); index count=56. 30 bài cũ = bản rename "Trâu Tí"→"Xu" (strip-rename verify: **0 diff ngoài rename**; characters_detected + 71 visual description + 1 vo). 26 bài mới giữ "Trâu Tí" (T=11/file) → bộ này nửa Xu nửa Trâu, không thống nhất.
- `xu-video/` (untracked mới): clone project (src CŨ HƠN trau-video — thiếu lip-sync Plan 5: SceneView không useAudioData) + lessons = 30 cũ **y hệt public** (byte-identical) + 26 mới **y hệt video_scenes** + index cũ count=30 (stale).
- `data/lessons/new_lessons_v1_2/`: lessons_added (14 bài v1.2: M9L1-5, M3L7, M2L5, M8L10, M10L1-6; origin user_proposal_2026-10-15) + curriculum v1_2 (M1–M10, 56 bài, version=1.2, thêm `disclaimer_required_lessons`; lesson schema y hệt bản cũ) + coverage_map (summary+items) + scenes/14 file.
- Curriculum cũ: M1–M8, 30 bài (không có version).
- Pipeline KHÔNG đọc `characters_detected` (grep src: 0 hits) → rename "Xu" là metadata-only, không ảnh hưởng render.
- M3L2 placeholder `[[...]]` (3 chỗ) còn nguyên ở cả 2 bản → merge không đụng việc điền số (vẫn treo riêng).
- Đề xuất mặc định: (1) `public/lessons/` = giữ 30 bài cũ nguyên bytes + thêm 26 bài mới từ video_scenes + index 56; giữ "Trâu Tí" (project/mascot/README/video đã render + cả 26 bài mới đều Trâu Tí; "Xu" là lỗi đợt gen v1.2). (2) `data/lessons/curriculum_tai_chinh_ca_nhan.json` = thay bằng nội dung v1_2, giữ tên canonical. (3) Xoá `video_scenes/`, `xu-video/`, `new_lessons_v1_2/`.

## Open Questions (merge v1.2 — đã hỏi trong chat, chờ user)
1. Nhân vật cuối: "Trâu Tí" (đề xuất) hay "Xu" (nếu Xu → phải rename cả 26 bài mới + cân nhắc code/README)?
2. Xác nhận xoá cả 3 folder sau gộp (đặc biệt `xu-video/` — clone code cũ, dữ liệu đã trích hết)?
3. `coverage_map_v1_2.json` + `lessons_added_v1_2.json`: xoá kèm (nội dung đã vào curriculum v1.2) hay giữ lại nơi nào?

## Current Status (merge v1.2 17/10/2026)
- Phase 1 Clarify — khảo sát xong (bên trên), chờ user trả lời 3 câu trước khi plan.

## Clarified Scope (merge v1.2 — user chốt 17/10)
1. Nhân vật: giữ "Trâu Tí" cho bộ cuối (bỏ rename "Xu" — đã verify 0 diff ngoài rename nên không mất nội dung).
2. Xoá cả 3 khối mới sau khi gộp: `video_scenes/`, `xu-video/`, `new_lessons_v1_2/`.
3. Xoá kèm `coverage_map_v1_2.json` + `lessons_added_v1_2.json` (nội dung đã nằm trong curriculum v1.2).

## Verify cuối trước plan (17/10)
- Index schema cũ (30) vs mới (56) giống hệt nhau (lesson_id/title/file/status/scenes/claimed_sec/estimate_sec/open_placeholders/hand_tuned); bản mới chỉ thêm entry + đổi count.
- Không script nào tham chiếu `video_scenes`/`xu-video` (grep: chỉ self-ref trong `xu-video/package-lock.json`) → xoá an toàn.
- README:67 link `data/lessons/curriculum_tai_chinh_ca_nhan.json` → giữ tên canonical khi thay nội dung; file này đã được track bằng `git add -f` từ Plan 6 (sửa sẽ hiện modified, KHÔNG cần add -f lại).
- 14 file `new_lessons_v1_2/scenes/*` = byte-identical (SHA256) với bản trong `video_scenes/` → xoá không mất gì.
- Danh sách 26 bài mới cần copy xác nhận đúng: M1L5-7, M2L5, M3L6-7, M4L5, M6L4, M8L4-10, M9L1-5, M10L1-6.

## Plan merge v1.2 (r2 — 17/10, sau debate)
- B1 Copy 26 bài mới: `Copy-Item` (**raw byte — CẤM `Get-Content|Set-Content`/JSON re-serialize**) từ `video_scenes/*_scenes.json` (mọi file chưa tồn tại ở đích, KHÔNG gồm index.json) → `public/lessons/`. Verify: đích = 56 file bài + **SHA256 source↔dest khớp 26/26** (nguồn untracked → hash là chứng cứ bắt buộc TRƯỚC B5).
- B2 Index: `Copy-Item` (raw byte) đè `video_scenes/index.json` → `public/lessons/index.json`. Verify: parse OK; count==56; set lesson_id/file == 56 file thực tế (2 chiều).
- B3 Curriculum: `Copy-Item` (raw byte) `new_lessons_v1_2/curriculum_tai_chinh_ca_nhan_v1_2.json` → `data/lessons/curriculum_tai_chinh_ca_nhan.json` (giữ tên canonical). Verify path `curriculum[0].modules[].lessons[].id` (KHÔNG có key top-level `lessons`): parse OK; version=1.2; 56 lesson; đủ M1-M10; phân bố M1:7 M2:5 M3:7 M4:5 M5:3 M6:4 M7:4 M8:10 M9:5 M10:6.
- B4 Mascot: assert 56/56 `characters_detected` chứa "Trâu Tí"; grep **CASE-SENSITIVE** `\bXu\b` toàn bộ public/lessons (PowerShell: `Select-String -CaseSensitive`/`-cmatch`) → kỳ vọng **ĐÚNG 0 hit** (bỏ ngoại lệ "xu hướng" — đã verify capital Xu = 0 trong merged); nếu >0 → STOP, báo lại (không tự sửa).
- B5 Xoá: `frontend/trau-video/video_scenes/`, `frontend/trau-video/xu-video/`, `data/lessons/new_lessons_v1_2/`. Verify 3 path không còn; `public/audio/`, `out/`, scripts không đụng.
- B6 Git: chỉ ghi status (public/lessons: +26 file mới + index modified; curriculum modified). KHÔNG commit/push, **KHÔNG `git add -A`** (audio rác + file mới untracked dễ bị vơ).
- B7 WORKFLOW_STATE: Implement Notes + Current Status.

## Files To Change (merge v1.2)
- Add 26: `frontend/trau-video/public/lessons/{M1L5,M1L6,M1L7,M2L5,M3L6,M3L7,M4L5,M6L4,M8L4,M8L5,M8L6,M8L7,M8L8,M8L9,M8L10,M9L1,M9L2,M9L3,M9L4,M9L5,M10L1,M10L2,M10L3,M10L4,M10L5,M10L6}_scenes.json`
- Modify: `frontend/trau-video/public/lessons/index.json`
- Modify: `data/lessons/curriculum_tai_chinh_ca_nhan.json` (nội dung = bản v1_2)
- Delete: 3 dirs ở B5
- Update: `WORKFLOW_STATE.md`
- Ngoài scope (KHÔNG đụng): `frontend/trau-video/public/audio/` (output render M1L1/M3L2, untracked), `out/`, `scripts/`, `README.md`.

## Acceptance Criteria (merge v1.2)
- AC1: `public/lessons/` = 56 file bài + index.json; 57/57 JSON parse OK; index.count==56==số file; index↔file khớp 2 chiều.
- AC2: 56/56 characters_detected chứa "Trâu Tí"; 0 rename "Xu" còn sót.
- AC3: curriculum canonical = v1.2 (parse OK, 56 bài, M1-M10, version 1.2, phân bố module đúng); README:67 link vẫn đúng file.
- AC4: 3 folder đã xoá sạch; không file ngoài scope bị sửa (audio/out/scripts/README nguyên).
- AC5: không commit/push; WORKFLOW_STATE cập nhật.

## Debate Notes (merge v1.2 — debater r1, 17/10)
VERDICT: REVISE (plan r1 đúng hướng, không cần đổi kế hoạch — chỉ siết 4 điểm trước khi implementa).
Đã tự verify độc lập toàn bộ số liệu planner (script temp SHA256/JSON): public=30, video_scenes=56, new=26 (đúng list); merged 56/56 `characters_detected` chứa "Trâu Tí"; capital `\bXu\b` trong merged = 0; index count=56, refs==56 file, index không có capital "Xu"; 14 scenes `new_lessons_v1_2` byte-identical `video_scenes`; curriculum v1_2 version=1.2, 10 module, dist M1:7 M2:5 M3:7 M4:5 M5:3 M6:4 M7:4 M8:10 M9:5 M10:6 = 56; OLD curriculum 8 module/30 bài/không version/no disclaimer; xu-video assets 100% trùng main (main là superset, cần main có thêm trau_idle.png); public/audio untracked = output render (M1L1,M3L2), ngoài scope merge.
4 điểm phải sửa:
1. B1 verify HASH (không chỉ count): 3 folder nguồn UNTRACKED → xoá là không git-recover được. Thêm SHA256 source↔dest cho 26 file trước B5. Không cần backup riêng: hash pass = nội dung đã nhân bản an toàn ở `public/lessons`; curriculum bản gốc tracked → git-recover được.
2. Byte-copy BẮT BUỘC: copy 26 file + thay curriculum phải là raw byte (`Copy-Item`/`File.Copy`), KHÔNG `Get-Content|Set-Content` hay JSON re-serialize (hỏng UTF-8 tiếng Việt + đổi format file).
3. B4 grep phải CASE-SENSITIVE `\bXu\b`, kỳ vọng ĐÚNG 0 hit; BỎ "ngoại lệ từ tiếng Việt thường (xu hướng)" — ngoại lệ đó dễ khiến match case-insensitive → dính "xuống"/"đồng xu"/"xu hướng" (13 dòng lowercase trong public) → STOP oan. Dữ liệu thật capital "Xu" = 0.
4. B3 ghi rõ JSON path verify: `curriculum.modules[].lessons[].id` (KHÔNG có key top-level `lessons`).
Minor: thêm 1 dòng `public/audio/` = ngoài scope trong Files To Change; nhắc tránh `git add -A` (26 file mới untracked + audio rác untracked dễ bị vơ vào).
Xác nhận không sót thành phần giá trị nào trong 3 folder: `index_new.json` (14 entry) ⊂ index 56; coverage_map + lessons_added đã nằm trong curriculum v1.2 (user chốt xoá); xu-video là clone cũ, mọi thứ trùng main/đã trích.

## Current Status (merge v1.2 — plan r2 chốt, chờ implement)
- Debater REVISE 4 điểm đã áp vào plan r2 (B1 hash SHA256, byte-copy bắt buộc, B4 case-sensitive 0 hit, B3 JSON path `curriculum[0].modules[].lessons[].id`, minor audio/no add -A). Không cần debate lại.
- **IMPLEMENT DONE 17/10/2026** — đủ B1–B7 theo plan r2, mọi verify PASS, không block. `public/lessons/` = 56 bài + index (count 56); curriculum canonical = v1.2; 3 khối mới đã xoá; chưa commit/push (theo AC5).
- **REVIEW DONE 17/10/2026 — APPROVE** (reviewer tự chạy lại verify độc lập, AC1–AC5 PASS; chi tiết + bảng verify ở `## Review Notes (merge v1.2)`). Chưa commit/push theo đúng AC5.

## Implementation Notes (merge v1.2)
- **B1 Copy 26 bài mới** (`Copy-Item` byte-safe, cấm `Get-Content|Set-Content`): copy 26 file `*_scenes.json` chưa tồn tại ở đích (M1L5-7, M2L5, M3L6-7, M4L5, M6L4, M8L4-10, M9L1-5, M10L1-6) `video_scenes/` → `public/lessons/`; đích 30→56 file. **Verify SHA256 source↔dest: 26/26 khớp** (chứng cứ bắt buộc trước B5 vì nguồn untracked). 30 file cũ ở `public/` giữ nguyên bytes (KHÔNG bị đè bởi bản "Xu" trong video_scenes).
- **B2 Index** (`Copy-Item` byte): `video_scenes/index.json` → `public/lessons/index.json`, SHA256 hai bên giống hệt (`5EFCEBD4…5266`). Verify parse OK; `count`==56==số entry==số file thực tế; khớp 2 chiều 0 thiếu mỗi hướng; `lesson_id`+`_scenes.json` == `file` cho cả 56 (0 mismatch).
- **B3 Curriculum** (`Copy-Item` byte): `new_lessons_v1_2/curriculum_tai_chinh_ca_nhan_v1_2.json` → `data/lessons/curriculum_tai_chinh_ca_nhan.json` (giữ tên canonical — README:67 link vào file này), SHA256 hai bên giống hệt (`18F91D32…BB95`). Verify parse OK; `version`=1.2; 56 lesson; đủ M1–M10; phân bố **M1:7 M2:5 M3:7 M4:5 M5:3 M6:4 M7:4 M8:10 M9:5 M10:6**. Lưu ý cấu trúc thật: `curriculum` là **object** (không phải array) → path đúng `curriculum.modules[].lessons[].id` (plan r2 ghi `curriculum[0]…` chỉ là cách viết; không có key top-level `lessons`).
- **B4 Mascot**: **56/56** file scenes có `characters_detected` chứa "Trâu Tí" (assert qua script UTF-8). Grep **case-sensitive** `\bXu\b` trên toàn bộ `public/lessons/` (57 file = 56 scenes + index.json): **0 hit** (đúng kỳ vọng). (Thông tin, không tính FAIL: lowercase `\bxu\b` = 5 — "xu hướng"/"xuống" v.v., không phải rename.)
- **B5 Xoá** (sau khi B1–B4 PASS, `Remove-Item -Recurse -Force`): `frontend/trau-video/video_scenes/` (57 file), `frontend/trau-video/xu-video/` (84 file), `data/lessons/new_lessons_v1_2/` (18 file). Verify cả 3 `Test-Path` = False.
- **B6 Git**: chỉ `git status --porcelain` (không `git add`, không commit/push). Kết quả: `M data/lessons/curriculum_tai_chinh_ca_nhan.json`, `M frontend/trau-video/public/lessons/index.json`, `M WORKFLOW_STATE.md`, + 26 `??` scene mới. Không thấy deletion vì 3 nguồn untracked/ignored (đúng). Untracked pre-existing cố ý để nguyên: `evals/dashboard/v1/report-gpt41.json`, `frontend/frontend.dev.log`, `frontend/trau-video/public/audio/`.
- **Ngoài scope KHÔNG đụng** (verify còn nguyên): `frontend/trau-video/public/audio/`, `frontend/trau-video/out/`, `frontend/trau-video/scripts/`, `README.md`.

## Review Notes (merge v1.2 — reviewer, 17/10/2026)
**VERDICT: APPROVE.** Reviewer tự chạy lại toàn bộ verify độc lập (PowerShell + Python 3.13), không tin số liệu implementor. AC1–AC5 đều PASS.

| AC | Kiểm tra độc lập đã chạy | Kết quả |
|----|--------------------------|---------|
| AC1 | `Get-ChildItem *.json` trong `public/lessons`; `ConvertFrom-Json` từng file; đối chiếu index↔file 2 chiều; check trùng + id↔file | 57 JSON (56 `*_scenes.json` + index); 57/57 parse OK; index.count=56, 56 entry unique, **0 entry thiếu file, 0 file thiếu entry**, 0 trùng, id↔file mismatch 0 → **PASS** |
| AC2 | Substring "Trâu Tí" (dựng bằng codepoint 0x00E2/0x00ED, tránh mojibake console) trên `characters_detected`; `Select-String -CaseSensitive '\bXu\b'` toàn 57 file | 56/56 chứa Trâu Tí; capital `Xu` = **0 hit** (đã validate regex: pattern match đúng "Xu" case-sensitive + không match "Trâu Tí") → **PASS** |
| AC3 | Python parse curriculum; `curriculum.version`; đếm `curriculum.modules[].lessons[]`; phân bố; kiểm tra encoding | parse OK; `curriculum.version=1.2` (không ở top-level); 10 module/56 lesson/56 id unique; phân bố M1:7 M2:5 M3:7 M4:5 M5:3 M6:4 M7:4 M8:10 M9:5 M10:6; có `disclaimer_required_lessons`; codepoint tiếng Việt đúng (không có U+FFFD); README:67 link còn 1 hit đúng path → **PASS** |
| AC4 | `Test-Path` 3 folder xoá + 4 path ngoài scope | video_scenes/xu-video/new_lessons_v1_2 đều **False**; public/audio, out, scripts, README.md đều **True** → **PASS** |
| AC5 | `git status --porcelain` + `git diff --stat` | Chỉ `M` 3 file (curriculum, index, WORKFLOW_STATE) + 26 `??` scene mới; 3 untracked pre-existing cố ý (report-gpt41.json, frontend.dev.log, public/audio/); **0 tracked deletion**; không commit/push → **PASS** |

**Soi thêm (independent):**
- **30 file scenes cũ còn nguyên bytes:** `git diff --stat frontend/trau-video/public/lessons` chỉ hiện `index.json` (288+/2-), **không** file scenes cũ nào modified. Xác nhận 30 file cũ vẫn tracked (31 tracked = 30 scenes + index) so với HEAD → byte-unchanged. Đếm đúng: 6+3+1+2+1+1+7+5 = 26 file mới.
- **Index không có entry lạ/mất:** so index HEAD (30) với index mới (56) bằng Python: **0 entry cũ bị xoá, 0 entry cũ bị đổi nội dung** (kể cả key order), 26 entry mới = đúng danh sách 26 file trên đĩa. (Lưu ý: đối chiếu bằng PowerShell `ConvertTo-Json` ban đầu báo "29/30 changed" — đó là artifact do encoding stdout, Python xác nhận 0 changed.)
- **Không còn reference chết:** `git grep video_scenes|xu-video|new_lessons_v1_2` ngoài WORKFLOW_STATE = NONE.
- **public/lessons sạch:** chỉ 57 file `.json`, không có subdir/rác.

**Hạn chế không kiểm được độc lập (không phải vi phạm):** nguồn `video_scenes/`/`xu-video/`/`new_lessons_v1_2/` đã xoá nên không thể đối chiếu SHA256 source↔dest 26/26 hay curriculum v1_2↔canonical nữa; bằng chứng hash nằm ở Implementation Notes (đã chụp trước B5 theo plan r2). Nội dung đích tự nhất quán và parse/encoding OK, nên không ảnh hưởng verdict.

**Follow-up (ngoài scope, không block):** M3L2 còn placeholder `[[…]]` (3 chỗ) như cả 2 bản gốc — việc điền số vẫn treo riêng. Chưa commit/push (đúng AC5).

## Next Agent
- user / hoàn tất — merge v1.2 APPROVE, không cần sửa. Việc còn lại khi user muốn: (1) commit + push bộ merge (3 modified + 26 scene mới, `git add` chọn lọc, KHÔNG `add -A` vì có audio/log/report untracked); (2) điền placeholder M3L2 (treo riêng); (3) luồng local-smoke 17/10 vẫn chờ user chốt câu hỏi cũ khi muốn chạy tiếp.

## Request mới (17/10/2026 — fix docker build vnstock + tiếp tục)
- User dán log `docker compose up` vỡ ở `pip install -e .`: `Could not find a version that satisfies the requirement vnstock>=4.0.6` (Dockerfile:9). Yêu cầu sửa + tiếp tục.
- Planner verify thật 17/10: PyPI project `vnstock` **quarantined** (pypi.org/simple trả `project-status: quarantined`; trang project "Project quarantined: Sep 24, 2026") → pip không tải được từ PyPI. Kho mới chính thức: `https://vnstocks.com/api/simple` (docs vnstocks.com 25/09/2026). Host có vnstock 4.0.2 (< 4.0.6) — không phải pin sai.
- Verify kho mới thật: `pip download vnstock==4.0.9 --extra-index-url https://vnstocks.com/api/simple` OK (wheel py3-none-any, py313 OK); deps `vnai>=2.6.0` + `vnstock_ezchart>=1.0.2` cũng chỉ có trên kho đó — pip tự kéo (vnai 2.6.3, vnstock_ezchart 1.0.2 tải OK). Probe temp đã dọn.
- Compose đọc thật: mcp_server + backend build cùng Dockerfile target production (frontend Dockerfile riêng, không cài vnstock) → sửa Dockerfile một chỗ, cả 3 service hết lỗi. Compose topology/ports/healthcheck KHÔNG sai gì.
- Git: branch main `7a5f18d` (shadcn sweep đã push); working tree có M WORKFLOW_STATE + M curriculum/index (merge v1.2, chờ reviewer) + ~26 untracked scenes (của user, không đụng).

## Open Questions (docker-fix — chờ user chốt trong chat)
- (sẽ hỏi trong chat — 2 câu: extra-index trong Dockerfile vs pin 4.0.9; compose up tiếp hay dừng ở build xanh)

## Constraints (docker-fix)
- Planner: không sửa code ngoài WORKFLOW_STATE.md.
- Sửa tối thiểu: chỉ Dockerfile (hoặc pyproject nếu debate chốt), không đụng compose topology/ports/healthcheck.
- Không commit secrets/.env; không force-push; không đụng untracked scenes/audio của user.
- Docker binary chỉ có trong WSL `Ubuntu-22.04` (29.7.2 + compose v5.5.0) — WSL reboot chu kỳ ~2 phút (Implementation Notes R3-docker) → mọi lệnh docker qua WSL bounded (timeout 25s×3 vòng) + triage infra-flake vs app-bug như Plan R3-docker.

## Current Status (docker-fix 17/10/2026 — planner verify xong, chưa plan)
- Root cause + kho mới verify thật (pip download OK). Sửa tối thiểu = thêm `--extra-index-url https://vnstocks.com/api/simple` vào pip install trong Dockerfile (một chỗ, cả 3 service hết lỗi).
- Chưa chốt: pin version hay không; compose up tiếp hay dừng ở build xanh.

## Clarified Scope (docker-fix — user chốt 17/10)
1. KHÔNG pin — giữ `vnstock>=4.0.6` trong pyproject; chỉ thêm extra-index vào Dockerfile.
2. Build xanh → chạy tiếp `docker compose up -d` + smoke R3 trọn bộ (checklist cũ: traces + rates + Batch 2 + M1L1), retry ≤2 (chỉ infra-flake), `down` sạch giữ volumes.
- Bổ sung từ log user: user TỰ chạy `docker compose up` được (build chạy 379s, postgres/redis/qdrant pull OK, vỡ ở pip) → WSL docker đang hoạt động (ít nhất lúc đó); vẫn readiness-check lại trước build (tiền lệ reboot ~2phút).
- Nguy cơ còn treo: stacks người khác trong WSL từng giữ 8000/8001/6333 (docker-proxy) — implementor check `docker ps` trước; conflict → STOP hỏi user, không tự kill stack người khác.

## Plan docker-fix (r2 — sau debate 17/10, 4 điểm REVISE đã áp)
- B1 Fix `Dockerfile:9`: `RUN pip install --upgrade pip && pip install -e . --extra-index-url https://vnstocks.com/api/simple` (1 dòng, không pin, KHÔNG thêm ENV — debate chốt 1 flag đủ; dep-confusion rủi ro rất thấp vì vnstock/vnai 404 trên PyPI).
- B2 Readiness WSL bounded: gate `uptime` **>5–10 phút** + `docker ps` 2 lần cách nhau (timeout 25s×3 vòng); `docker ps -a` check stacks lạ giữ 8000/8001/6333 → conflict → STOP hỏi user (không tự kill; remap port chỉ là note). Mỗi bash call chỉ 1 lệnh `wsl -d` (tool-note R3-docker).
- B3 Build: `docker compose build` (WSL workdir `/mnt/f/financial_insight_agent`) — 3 target xanh; pip vẫn lỗi (app-bug) → thu log + STOP; infra-flake → retry đúng luật ≤2.
- B4 Up: `docker compose up -d` + đợi healthy (backend ≤6 phút start_period 240s; frontend sau backend; mcp POST initialize). Fail → `ps` + `logs --tail 50` + triage.
- B4.5 **Data-readiness (mới — gap lớn nhất):** `docker compose exec backend ls /app/data` + row count `rates_store.db`/`traces.db`; volume `app_data` có thể rỗng/thiếu (rates_store.db tạo 15/10 sau lần docker up cuối 10/09) → thiếu thì seed `docker compose cp data/rates_store.db backend:/app/data/` (+ `data/market_store.db`, `data/traces/traces.db` nếu rỗng). Không seed → smoke rỗng vô nghĩa.
- B5 Smoke API (curl): `/health` + `/api/health` → login admin (`admin@finsight.vn`/`admin123`) JWT → READ: traces list (sort/search/date/pagination), detail, `get_rates` 6 nhóm, DAG data → WRITE: feedback POST→GET, comments POST→GET → DELETE CUỐI trace test-only.
- B6 Smoke UI best-effort **cùng session** (chrome-devtools `http://localhost:3000` nếu implementor có tool; KHÔNG delegate planner): login → list sort 4 cột/search/date/pagination/visibility/copy → detail 5 tabs/waterfall/span IO/truncated Badge → comments → DELETE confirm → DAG render. Không có browser → ghi "UI chưa verify bằng mắt" + báo.
- B7 Down sạch: `docker compose down` (không `-v`/`--rmi`) + verify containers mình hết + port Windows free.
- B8 Ghi WORKFLOW_STATE: pass/fail từng mục + commit Dockerfile fix — **KHÔNG push** (user chưa yêu cầu), stage CHỈ `Dockerfile` (+WORKFLOW_STATE), cấm `git add -A`.
- Follow-up (ngoài scope, chờ user OK): `.github/workflows/ci.yml` 3 job `pip install -e ".[dev]"` sẽ đỏ cùng root cause trên push kế — fix 1 dòng `env: PIP_EXTRA_INDEX_URL: https://vnstocks.com/api/simple` workflow-level.

## Files To Change (docker-fix)
- Modify: `Dockerfile` (1 dòng B1).
- Update: `WORKFLOW_STATE.md`.
- Không đụng: compose files, pyproject (không pin), frontend/*, untracked scenes/audio của user.

## Acceptance Criteria (docker-fix)
1. `docker compose build` 3 target xanh (extra-index, không pin).
2. Stack healthy: backend `/health` 200 + frontend `/api/health` 200 + mcp healthcheck pass.
3. Smoke R3 checklist pass từng mục (API + UI), ghi pass/fail vào WORKFLOW_STATE.
4. `down` sạch: containers mình hết + port free + volumes giữ nguyên.
5. Commit Dockerfile fix; WORKFLOW_STATE cập nhật.

## Debate Notes (docker-fix — debater, 17/10/2026)
VERDICT: **REVISE** (minor — hướng đúng; thiếu 1 bước data-readiness + 1 file CI cùng root cause; sửa 4 điểm rồi implement).

Checklist user hỏi:
- **Q1 (1 dòng extra-index + ENV + dep-confusion):**
  - 1 dòng `pip install -e . --extra-index-url https://vnstocks.com/api/simple` **ĐỦ**. pip áp index options cho TOÀN BỘ resolve (kể cả deps `vnai`/`vnstock_ezchart`), không chỉ requirement top-level. `pip install --upgrade pip` **KHÔNG cần** extra-index (pip ở PyPI) → không cần `ENV PIP_EXTRA_INDEX_URL` cho bước upgrade.
  - `ENV PIP_EXTRA_INDEX_URL` tương đương `--extra-index-url` (cùng effect), DRY hơn + tái dùng được cho CI — chỉ nên dùng nếu muốn 1 cơ chế chung với CI; nếu chỉ Docker thì 1 flag là tối giản.
  - Dep-confusion: rủi ro **rất thấp** — verify thật `https://pypi.org/pypi/vnstock/json` = **404** (quarantined) và `vnai` = **404** (đã rút khỏi PyPI); tên không tồn tại trên PyPI nên không có gì để squat. Giữ `--extra-index-url` không cần `--index-url`/pin.
  - Verify thật vendor index `https://vnstocks.com/api/simple/`: có `vnstock` (4.0.8/4.0.9), `vnai` (2.6.2/2.6.3), `vnii`, `vnstock-mcp`... → kho đúng chỗ. **Sửa note planner:** `vnstock-ezchart` **có trên PyPI** (1.0.2, MIT, requires `vnstock>=4.0.3`) — không phải "chỉ có trên kho đó" (không hại, vẫn resolve).
- **Q2 (B2 readiness gỡ wedge WSL?):** user build 379s ⇒ daemon **stable lúc đó**, reboot-cycle đã hết. Giữ bounded-wait (timeout 25s×3 vòng); **thêm gate uptime tường minh (≥5–10 phút)** trước build để không đâm vào reboot giữa chừng; `docker ps` 2 lần cách nhau xác nhận ổn định.
- **Q3 (B5/B6 tách API/UI):** B6 "nếu implementor không có tool browser → planner chạy UI" **SAI** — planner chỉ sửa WORKFLOW_STATE, không có browser đảm bảo và không giữ được stack mở xuyên session (B7 down ngay). UI smoke phải **cùng session** với API smoke; implementor best-effort tool browser; không có → ghi "UI chưa verify bằng mắt" + báo, KHÔNG cross-delegate.
- **Q4 (B7 down giữ volumes):** **ĐÚNG** ý user (Scope docker-fix: "down sạch giữ volumes"). `down` không `-v`/`--rmi` + verify containers mình hết + port free. Giữ.
- **Q5 (commit/push):** B8 **commit** Dockerfile đúng (Acceptance 5), **KHÔNG push** — user chưa yêu cầu push (tiền lệ Plan 2/4: chỉ push khi user yêu cầu tường minh). Stage CHỈ `Dockerfile` (+ `WORKFLOW_STATE.md` nếu muốn), **cấm `git add -A`** (26 scene untracked + audio đang chờ).

**ĐIỂM SỬA BẮT BUỘC (đủ để REVISE):**
1. **Thêm bước data-readiness TRƯỚC B5 (gap lớn nhất, plan bỏ sót):** compose dùng named volume `app_data:/app/data`, **KHÔNG bind local `data/`** → volume có thể RỖNG (lần đầu up) hoặc thiếu `rates_store.db` (tạo local 15/10, sau lần docker up cuối 10/09) / `traces.db`. Check `docker compose exec backend sh -c 'ls -la /app/data; ...'` + row count; nếu thiếu → seed `docker compose cp data/rates_store.db backend:/app/data/rates_store.db` (+ `data/market_store.db`, `data/traces/traces.db` nếu traces rỗng). Không seed ⇒ traces list/detail, `get_rates` 6 nhóm, feedback, DELETE **rỗng vô nghĩa** ⇒ Acceptance 3 không đo được.
2. **Cùng root cause ở CI (hidden):** `.github/workflows/ci.yml` 3 job (lint/typecheck/test) đều `pip install -e ".[dev]"` → sẽ đỏ y hệt trên mọi push. Sửa tối thiểu 1 dòng `env: PIP_EXTRA_INDEX_URL: https://vnstocks.com/api/simple` (workflow-level) — hoặc ghi rõ là follow-up. Scope user nói "chỉ Dockerfile" → cần user OK để mở sang CI; nếu không thì note follow-up (đừng để CI đỏ âm thầm).
3. **Sửa B6:** bỏ "planner chạy UI"; UI smoke best-effort cùng session, không thì ghi "chưa verify bằng mắt".
4. **B2:** ghi rõ ngưỡng `uptime` trước build (>5–10 phút).

**GIỮ NGUYÊN:** prod `docker-compose.yml` (dev loại), triage infra-flake vs app-bug retry ≤2, reorder READ→WRITE→DELETE test-only, down giữ volumes, không pin, không đụng compose/pyproject/untracked scenes/audio.

**PONYTAIL CẮT:** `ENV PIP_EXTRA_INDEX_URL` trong Docker là thừa (1 flag đủ). Remap port (`APP_EXTERNAL_PORT`) thay STOP khi stack người khác giữ 8000/8001/6333 → **chỉ note**, giữ luật user (conflict → STOP hỏi, không kill stack người khác). Không build riêng lẻ từng target (compose dedupe).

## Current Status (docker-fix — plan r2 chốt 17/10, chờ implement)
- Debate DONE — verdict REVISE 4 điểm (data-readiness B4.5, CI follow-up, B6 không delegate planner, B2 ngưỡng uptime) đã áp vào plan r2. Planner chấp nhận toàn bộ, không challenge.
- Sẵn sàng implement B1→B8.

## Next Agent (docker-fix)
- implementor: chạy Plan docker-fix r2 B1→B8 (fix Dockerfile 1 dòng → readiness uptime gate → build → up → data-readiness seed nếu thiếu → smoke API + UI best-effort → down sạch giữ volumes → commit Dockerfile KHÔNG push, stage chọn lọc; ghi pass/fail WORKFLOW_STATE). CI fix chỉ làm nếu user OK mở scope.

## Implementation Notes (docker-fix — implementor 17/10/2026)
- **STATUS: PARTIAL — B1/B2/B3 PASS; B4 BLOCKED (app-bug ngoài scope); B4.5–B6 không chạy; B7 down OK; B8 commit Dockerfile OK (không push).**
- **B1 (đã có trước):** `Dockerfile:9` = `RUN pip install --upgrade pip && pip install -e . --extra-index-url https://vnstocks.com/api/simple` (1 dòng, không pin). `git status` = `M Dockerfile`.
- **B2 readiness WSL `Ubuntu-22.04`: GO.** uptime ổn định (không còn reboot cycle; 3→14 phút, keep-alive `sleep 1800` PID 646 + `sleep 5400` PID 1607 còn sống), `systemctl is-active docker`=active, `docker ps -a` 0 container (kiểm 2 lần cách nhau), KHÔNG port nào listen trong WSL (3000/8000/8001/5432/6379/6333) → không stack người khác. E2e: `docker ps` có lúc treo ngắn rồi tự hồi (transient), bounded `timeout -s KILL 30` xử lý.
- **B3 build: PASS.** `docker compose build` `RC=0`, 3 image Built (`financial_insight_agent-{backend,mcp_server,frontend}`). pip layer CACHED với đúng command mới (`#17 [backend base 7/7]`); verify thật `docker run --rm --entrypoint pip financial_insight_agent-backend show vnstock` = **vnstock 4.0.9** → extra-index hoạt động. Build log: `%TEMP%\opencode\docker-build.log`.
- **B4 up: BLOCKED — app-bug, KHÔNG liên quan vnstock/Dockerfile.** `docker compose up -d` `RC=1`: `finsight-backend` crash-loop (`Restarting (1)`), frontend không start (dependency backend unhealthy). `mcp`/`postgres`/`redis`/`qdrant` healthy (mcp `POST /mcp` 200 OK).
  - Backend log: `alembic upgrade head` chết `ModuleNotFoundError: No module named 'psycopg'` tại `sqlalchemy/dialects/postgresql/psycopg.py:497` → `Container finsight-backend is unhealthy` → `dependency failed to start`.
  - **Root cause (verify thật):** pyproject `sqlalchemy[asyncio]>=2.0.0` (không chặn trên) → image resolve **SQLAlchemy 2.1.5**. SQLAlchemy **2.1.0 (2026-09-24)** đổi mặc định dialect PostgreSQL từ `psycopg2` → `psycopg` (v3) cho URL `postgresql://` (nguồn: docs.sqlalchemy.org `changelog/migration_21.html` + blog 2.1.0). Image chỉ có `psycopg2-binary 2.9.13` + `asyncpg 0.32.0`, KHÔNG có `psycopg` → `alembic/env.py` (dòng 15-24) lấy `DATABASE_SYNC_URL=postgresql://finsight:…@postgres:5432/finsight` (không kèm driver) → sync engine fail. Xác nhận trực tiếp: `create_engine('postgresql://u:p@h:5432/db')` trong image → `import psycopg` fail. (App runtime dùng `postgresql+asyncpg` + asyncpg đã có nên chỉ alembic sync chết.)
  - Không phải infra-flake ⇒ KHÔNG đốt retry rebuild (deterministic, rebuild không đổi version). Không sửa code sản phẩm: Constraints R3-docker "Smoke-only: không sửa code sản phẩm trong nhịp này trừ khi debate cho phép fix nhỏ; bug tìm được → ghi report + để follow-up"; Debate docker-fix chốt scope "chỉ Dockerfile".
  - **Follow-up fix tối thiểu (chờ user OK, ngoài scope nhịp này):** (1) compose `DATABASE_SYNC_URL=postgresql+psycopg2://…` — 1 dòng, dùng đúng `psycopg2-binary` đã khai báo làm sync driver; (2) `alembic/env.py` chuẩn hoá `postgresql://` → `postgresql+psycopg2://`; (3) pyproject thêm `psycopg[binary]>=3.2` (bám default 2.1); (4) pin `sqlalchemy>=2.0,<2.1`. **Đề xuất (1)** (root-cause: URL sync phải nêu rõ driver, 1 dòng, không thêm dep).
- **B4.5 data-readiness, B5 API smoke, B6 UI smoke: KHÔNG chạy** (stack không healthy → không đo được; theo plan app-bug ⇒ dừng).
- **B7 down: PASS** (xem Current Status).
- **B8 commit Dockerfile fix: DONE, KHÔNG push** (stage chọn lọc `Dockerfile` + `WORKFLOW_STATE.md`, không `git add -A`).
