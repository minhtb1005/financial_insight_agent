# News source spike — decision record (Phase 3, 10/09/2026)

Timebox. Env thử: `C:\Users\DELL\AppData\Local\Temp\opencode\spike_env`
(pip `--target`, không chạm deps chính). Chỉ lưu title+excerpt+link+date.

## 1. vnnews (git+https://github.com/thinh-vu/vnnews.git) — LOẠI
- `pip install` **thất bại**: build error khi git clone (repo bỏ hoang từ
  2022, khớp排查 WORKFLOW_STATE §Library verification). Không fetch được gì.
- Kết luận: không dùng được, không cần đánh giá thêm.

## 2. vnewsapi (PyPI 0.1.0) — KHÔNG DÙNG NGUYÊN TRẠNG
- Cài OK. Hỗ trợ 10 sites (cafef, cafebiz, vietstock, vnexpress, ...).
- **CafeF**: 2 RSS URL hard-code đều 404
  (`/rss/tin-moi-nhat.rss`, `/rss/thi-truong-chung-khoan.rss` → 404).
  Fallback sitemap crawl **không giới hạn**: `get_articles(limit=5)` bò qua
  toàn bộ sitemap index (>200 child sitemaps, hàng trăm nghìn URL), >2 phút
  vẫn chưa xong (timeout 120s). Không dùng được cho adapter theo ticker.
- **VietStock**: RSS hard-code (`/rss/tin-moi-nhat.rss`) trả về **HTML
  200** (trang web, không phải XML) → feedparser parse được **0 entries**.
  Chưa tìm được feed XML đúng trong timebox (homepage không có autodiscovery).
- Sitemap path chỉ cho URL (+lastmod), **thiếu title/excerpt** → rớt tiêu chí
  completeness.
- Kết luận: lib còn non (config stale, không bound sitemap). Chỉ đáng tái dùng
  ý tưởng (RSS-first + CSS selectors cho `get_article_details`), không chốt dep.

## 3. Fallback RSS thuần (feedparser) — CHỌN
- CafeF với URL đúng pattern **`https://cafef.vn/<chuyen-muc>.rss`**
  (VD `/thi-truong-chung-khoan.rss` → 200): **50 entries**, đủ cả 4 trường
  title/link/published/summary. Verify 10/09/2026 (tin STB vượt đỉnh...).
- VietStock: chưa có feed XML xác minh → để ngỏ cho phase adapter (thử sitemap
  có bound `limit` + `get_article_details`, hoặc nguồn khác trong 10 sites).
- Không thêm dep mới vào `pyproject.toml`: `feedparser` đã có mặt
  (vnewsapi kéo vào spike env; check: chưa có trong deps chính → khi code
  adapter mới thêm `feedparser`).

## 4. Điểm cắm adapter mới (chưa code, đề xuất)
- `NewsPort.fetch_news(ticker)` giữ nguyên signature
  (`src/infrastructure/adapters/news_adapter.py` hiện dùng `Company.news()`
  nguồn VCI, hay rỗng).
- Thêm `RssNewsAdapter(NewsPort)`: bảng `SITE_FEEDS` (site → RSS URL đúng đã
  verify), fetch feedparser → lọc theo ticker trong title/summary → map về
  `{title, content=excerpt, source, url, date, ticker}`; cache TTL sẵn có ở
  `NewsSentimentService._fetch_single_news` (`NEWS_TTL_HOURS`) tái dùng được.
- Sentiment: thay `_classify_sentiment` keyword (giữ làm fallback) bằng 2 tầng:
  (a) HF `Marky12345/BigData_2026` (Bullish/Bearish/Uncertainty → pos/neg/neu),
  (b) LLM gpt-4o-mini `{label, score, rationale}` khi cần rationale. Xem §5.

## 5. Benchmark as-is trên tập nhãn tay (45 tin, 14 pos / 14 neu / 17 neg)
- `evals/golden/news_sentiment_labels.jsonl` (3 tin đầu fetch thật CafeF
  10/09/2026, còn lại viết tay đa dạng ngành, có case phủ định/khó).
- `evals/run_news_sentiment_eval.py`:
  - keyword as-is: **accuracy 0.5778 / macro-F1 0.5574**
    (F1 pos 0.68 / neu 0.53 / neg 0.45 — yếu nhất ở neg).
  - `Marky12345/BigData_2026` as-is, CPU (verify: tồn tại, license **MIT**,
    `config.json` RobertaForSequenceClassification, 3 labels đúng như model
    card, base `vinai/phobert-base-v2`): **accuracy 0.9111 / macro-F1 0.9069**
    (pos 0.93 / neu 0.85 / neg 0.94). Latency CPU ~**318 ms/tin**.
- Quyết định: HF as-is đã vượt xa keyword → **DỪNG, không LoRA/adapt**
  (đúng điều kiện Plan Phase 3 §4a). Lưu ý trung thực: tập nhãn tay do chính
  implementor viết nên số mang tính chỉ báo; nên mở rộng nhãn độc lập trước
  khi chốt default v1/v2.
