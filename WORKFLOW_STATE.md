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
