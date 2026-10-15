"""Pilot scope for the market-data pipeline (Phase 4a).

Single source of truth for which tickers/fields the ingest jobs cover.
Derived from the audit in docs/pipeline_pilot_scope.md (36 golden + 102
dashboard cases).
"""

PILOT_TICKERS: list[str] = [
    "VCB", "HPG", "FPT", "VNM", "MWG",
    "BID", "TCB", "VIC", "MSN", "CTG",
    "GAS", "MBB", "VHM", "PLX", "HSG",
]

# Ratio fields served by get_financial_ratios (snapshot schema readiness;
# upstream vnstock financial_statement is currently broken, so ingest stores
# whatever the source returns and skips tickers that error).
RATIO_FIELDS: list[str] = [
    "pe", "pb", "roe", "eps",
    "current_ratio", "debt_to_equity", "profit_margin",
    "quick_ratio", "asset_turnover", "dividend_yield",
]

# Daily history backfill start (per data-source availability ~2010-2012).
BACKFILL_START = "2012-01-01"

# Refresh cadence for "today" prices (minutes) — non-realtime by design.
REFRESH_MINUTES = 15

# Refresh lookback overlap (days) to also catch late corrections.
REFRESH_LOOKBACK_DAYS = 7
