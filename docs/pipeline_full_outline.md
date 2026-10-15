# Pipeline Full Scope — Outline (Phase 4b, chưa triển khai)

Trạng thái pilot (4a, đã verify): 15 mã, **50.587 rows / 7,9 MB**
(`data/market_store.db`), daily OHLCV 2012 → hôm nay, read-through +
freshness, scheduler 15p in-app. Outline dưới đây chỉ làm khi pilot cạn
dư địa — không code trong gói này.

## 1. Toàn sàn (mở rộng coverage)

- Quy mô ước tính: ~1.500–1.700 mã (HOSE ~400 + HNX ~330 + UPCOM ~880) →
  daily history ≈ **5–6M rows / ~0,9 GB** (ngoại suy từ 3.372 rows +
  ~0,53 MB/mã của pilot). Vượt ngưỡng sqlite đơn-file thoải mái.
- Thứ tự mở rộng: VN30 → VN100 → HNX30 → toàn HOSE → HNX → UPCOM (mỗi nấc
  re-validate hit-rate + latency p95 trước khi đi tiếp).
- Backfill toàn sàn ở Guest 20 req/phút ≈ 1.600 calls ≈ **2 ngày chạy nền**
  (kể cả resume) — hoặc key Community (60/phút) còn ~9 giờ. Quyết định key
  trước khi chạy.
- Danh sách mã động: lấy từ vnstock listing (không hard-code như pilot),
  delisted → đánh dấu, không xóa lịch sử.

## 2. Intraday (2–3 năm gần nhất)

- Khung được vnstock hỗ trợ: 1m/5m/15m (`VNStockClient`, interval 1d/1m/...
- Thể tích: 1 phút ≈ 270 bars/ngày × 250 phiên ≈ 67k rows/mã/năm →
  15 mã pilot ≈ **1M rows/năm**, toàn sàn ≈ **100M+ rows/năm** → bắt buộc
  postgres + partition theo tháng + retention job (chỉ giữ 2–3 năm, rollup
  sang daily khi quá hạn).
- Table mới: `prices_intraday(ticker, datetime, interval, o/h/l/c/v, ...)`
  + mở rộng `CachedMarketDataAdapter` (pilot hiện chỉ cache `1d`, các
  interval khác delegate trực tiếp).
- Ưu tiên 15 mã pilot trước, đo latency rồi mới mở rộng.

## 3. Market events — CHƯA LÀM (không có consumer)

- Đã kiểm chứng: không tool nào trong `mcp_server/` tiêu thụ events
  (`market_events` module không tồn tại trong codebase hiện tại).
- Chỉ triển khai khi có tool consumer được duyệt (VD cảnh báo sự kiện/
  chia cổ tức), kèm golden cases + eval riêng như RAG.

## 4. Postgres migration (trigger, không làm trước)

- Trigger: ghi/đọc đồng thời (scheduler + N replicas/API workers) **hoặc**
  DB > vài GB. Pilot hiện: 1 writer (scheduler) + readers cùng process —
  sqlite WAL đủ.
- Đường đi: `MarketStore` hiện dùng `sqlite3` stdlib → bọc sau interface
  `MarketStore` (không đổi callers): triển khai `PostgresMarketStore`
  (SQLAlchemy async đã có trong deps: `sqlalchemy[asyncio]`, `asyncpg`;
  compose đã có service postgres `finsight`), chọn backend qua env
  `MARKET_STORE_URL` (default sqlite file hiện tại).
- Alembic migration script cho 3 tables + index (ticker, date).

## 5. Cron ngoài (trigger, không làm trước)

- Trigger: scale nhiều replica (BackgroundScheduler in-app sẽ chạy trùng
  job). Khi đó: 1 scheduler rời (cron/K8s CronJob) + lock phân tán
  (Redis `SET NX`, Redis đã có trong compose nhưng local đang chạy không
  Redis — quyết định hạ tầng trước).
- Hiện tại giữ `start_market_scheduler` in-app (đơn replica).

## 6. Ratios snapshot (nợ từ 4a)

- Schema + accessor đã sẵn (`ratios_snapshot`). Ingest/wiring chỉ làm khi
  upstream vnstock sửa `financial_statement` (hiện hỏng — đã verify).
- Khi nguồn hồi phục: ingest snapshot theo quý + read-through trong
  `FinancialRatioService` (giữ fallback live), re-run ratio cases.

## 7. Gate trước khi coi 4b xong (mỗi nấc)

- Subset benchmark rerun (như 4a: 6 cases, numeric 1.000) + hit-rate log
  (mục tiêu store-hit >90% ở mã phủ sóng) + latency p95 không tăng quá 20%
  so baseline + `compare_reports.py` gate 2% + golden re-validate
  (đặc biệt case realtime/"today").
