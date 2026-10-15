# Pipeline Pilot Scope (Phase 4a)

Audit từ 36 golden cases (`evals/golden/golden_dataset.jsonl`) + 102 dashboard cases
(`evals/dashboard/v1/benchmark.jsonl`) — script: temp `audit_pilot.py`.

## Tickers pilot (15 mã, theo tần suất xuất hiện)

VCB (56), HPG (44), FPT (42), VNM (38), MWG (29), BID (20), TCB (19),
VIC (18), MSN (18), CTG (17), GAS (13), MBB (7), VHM (4), PLX (4), HSG (3).

Long-tail (fallback vnstock trực tiếp khi miss, 1–2 lượt nhắc):
CMG, ELC, ITG, FRT, PNJ, NKG, VRE, PVD, VPB, DGW.
Bỏ qua false-positive regex: SMA/ROE/RSI/MACD/EPS (tên chỉ báo), XYZABC (edge case mã ảo).

## Fields pilot

- Daily OHLCV: `open, high, low, close, volume` (phủ `get_stock_price`,
  `calculate_technical_indicator` SMA/RSI/MACD, `compare/rank/aggregate`,
  `check_price_alert`, `forecast_stock_price`, `manage_portfolio`).
- Ratio snapshot: `pe, pb, roe, eps, current_ratio, debt_to_equity,
  profit_margin, quick_ratio, asset_turnover, dividend_yield`
  (phủ `get_financial_ratios`; hiện upstream vnstock hỏng — pipeline lưu
  snapshot để khi nguồn hồi phục chỉ cần refresh, không đổi code tool).
- Dashboard metrics: `close, volume, pe, roe, eps, revenue, profit, risk, return`
  (mock hiện tại — pipeline dùng khi dashboard chuyển sang dữ liệu thật).

## Không làm trong pilot

- `events`/market_events (chưa tool nào tiêu thụ).
- Intraday (chỉ khi sang 4b).
- Postgres, cron ngoài (sqlite + `start_scheduler` in-app).

## Refresh

- Backfill 1 lần: daily từ ~2010-2012 (tùy mã, theo mốc khả dụng VCI/TCBS/KBS).
- Refresh "today": mỗi 10-20 phút qua `start_scheduler`; tool output kèm
  `data_as_of` công khai (chấp nhận non-realtime).
- Rate limit Guest 20 req/phút → ingest chunked-resumable (pattern đã chứng
  minh ở GPT-4.1 benchmark run).
