from typing import Any
from shared.constants import RATIO_TTL_HOURS
from shared.base_service import BaseService
from shared.ports.cache_port import CachePort
from shared.ports.financial_port import FinancialPort


def _ensure_float(v, default: float = 0.0) -> float:
    if v is None:
        return default
    try:
        f = float(v)
        return f if f == f else default
    except (ValueError, TypeError):
        return default


class FinancialRatioService(BaseService):
    def __init__(self, cache: CachePort, financial_port: FinancialPort, store: Any | None = None) -> None:
        super().__init__("financial_ratio_service", cache)
        self._financial = financial_port
        self._store = store

    def handle_query(
        self,
        tickers: list[str],
        field: str = "pe",
    ) -> dict[str, Any]:
        """Truy vấn chỉ số tài chính cho danh sách mã chứng khoán.

        Args:
            tickers: Danh sách mã chứng khoán.
            field: Loại chỉ số cần lấy.

        Returns:
            Dict chứa chỉ số tài chính cho từng mã.
        """
        err = self._require_tickers(tickers)
        if err:
            return err

        return self.for_each_ticker(tickers, lambda t: self._fetch_single(t, field))

    def _store_or_none(self) -> Any | None:
        # No lazy default: the store is wired explicitly in production
        # (dependencies.py) so unit tests with FakePorts can never
        # side-effect the real data/market_store.db via write-back.
        return self._store

    def _fetch_single(self, ticker: str, field: str) -> dict[str, Any]:
        # DB-first: snapshot read-through (quarterly cadence, never worse
        # than live — miss falls through to the port + cache path below).
        store = self._store_or_none()
        if store is not None:
            try:
                snap = store.get_ratios(ticker)
                if snap and field in snap:
                    freshness = {}
                    if snap.get("_fetched_at"):
                        freshness = {
                            "data_as_of": snap["_fetched_at"],
                            "data_source": snap.get("_source", "db"),
                        }
                    entry = _snapshot_entry(field, float(snap[field]), snap.get("_period"), freshness)
                    if entry:
                        return entry
            except Exception:
                pass
        result = self._cached_fetch(
            "financial_ratio",
            ticker,
            lambda: get_financial_ratios(self._financial, ticker, field, {"requested_field": field}, cache=self._cache),
            ttl_hours=RATIO_TTL_HOURS,
            ratio_type=field,
        )
        # Best-effort write-back of computed canonical values.
        if store is not None and isinstance(result, dict) and "error" not in result:
            try:
                payload = {
                    name: entry.get("value")
                    for name, entry in result.items()
                    if isinstance(entry, dict) and entry.get("value") is not None
                    and not str(name).startswith("data_")
                }
                period = next(
                    (e.get("time_range") for e in result.values()
                     if isinstance(e, dict) and e.get("time_range")),
                    None,
                )
                if payload:
                    store.save_ratios(ticker, payload, period=period, source="vnstock")
            except Exception:
                pass
        return result







def get_pe_interpretation(pe_ratio: float) -> str:
    if pe_ratio < 10:
        return "Low P/E - Potentially undervalued or company has issues"
    elif pe_ratio < 20:
        return "Moderate P/E - Reasonable valuation"
    elif pe_ratio < 30:
        return "High P/E - Potentially overvalued or high growth expectations"
    else:
        return "Very high P/E - Significant overvaluation risk"


def get_pb_interpretation(pb_ratio: float) -> str:
    if pb_ratio < 1:
        return "Low P/B - Potentially undervalued"
    elif pb_ratio < 3:
        return "Moderate P/B - Reasonable valuation"
    else:
        return "High P/B - Potentially overvalued"


def get_roe_interpretation(roe: float) -> str:
    if roe < 5:
        return "Low ROE - Poor profitability"
    elif roe < 15:
        return "Moderate ROE - Acceptable profitability"
    elif roe < 25:
        return "Good ROE - Strong profitability"
    else:
        return "Excellent ROE - Exceptional profitability"


def get_eps_interpretation(eps: float) -> str:
    if eps < 0:
        return "Negative EPS - Company is losing money"
    elif eps < 1:
        return "Low EPS - Modest profitability"
    elif eps < 5:
        return "Moderate EPS - Good profitability"
    else:
        return "High EPS - Strong profitability"


def get_current_ratio_interpretation(current_ratio: float) -> str:
    if current_ratio < 1:
        return "Poor liquidity - Potential solvency issues"
    elif current_ratio < 1.5:
        return "Adequate liquidity - Acceptable short-term health"
    elif current_ratio < 3:
        return "Good liquidity - Strong short-term financial health"
    else:
        return "Very high liquidity - May indicate inefficient asset use"


def get_debt_to_equity_interpretation(debt_to_equity: float) -> str:
    if debt_to_equity < 0.5:
        return "Low leverage - Conservative capital structure"
    elif debt_to_equity < 1.5:
        return "Moderate leverage - Balanced capital structure"
    elif debt_to_equity < 2.5:
        return "High leverage - Aggressive capital structure"
    else:
        return "Very high leverage - High financial risk"


def get_profit_margin_interpretation(profit_margin: float) -> str:
    if profit_margin < 0:
        return "Negative margin - Company is losing money"
    elif profit_margin < 5:
        return "Low margin - Thin profitability"
    elif profit_margin < 15:
        return "Moderate margin - Reasonable profitability"
    elif profit_margin < 25:
        return "Good margin - Strong profitability"
    else:
        return "Excellent margin - Exceptional profitability"


def get_quick_ratio_interpretation(quick_ratio: float) -> str:
    if quick_ratio < 1:
        return "Poor liquidity - May struggle with immediate obligations"
    elif quick_ratio < 1.5:
        return "Adequate liquidity - Can meet short-term obligations"
    else:
        return "Strong liquidity - Excellent short-term financial health"


def get_asset_turnover_interpretation(asset_turnover: float) -> str:
    if asset_turnover < 0.5:
        return "Low efficiency - Poor asset utilization"
    elif asset_turnover < 1.5:
        return "Moderate efficiency - Acceptable asset utilization"
    elif asset_turnover < 3:
        return "Good efficiency - Strong asset utilization"
    else:
        return "Excellent efficiency - Outstanding asset utilization"


def get_dividend_yield_interpretation(dividend_yield: float) -> str:
    if dividend_yield < 1:
        return "Low yield - Minimal income generation"
    elif dividend_yield < 3:
        return "Moderate yield - Reasonable income generation"
    elif dividend_yield < 5:
        return "Good yield - Strong income generation"
    else:
        return "High yield - Very strong income generation (may be unsustainable)"


_RATIO_ENTRIES: dict[str, dict[str, Any]] = {
    "pe": {
        "key": "pe_ratio",
        "extract": lambda row, market: {
            "eps": _ensure_float(row.get("eps")),
            "current_price": market.get("current_price", 0),
        },
        "guard": lambda vals: vals["eps"] != 0 and vals["current_price"],
        "compute": lambda vals: vals["current_price"] / vals["eps"],
        "interpret": get_pe_interpretation,
    },
    "pb": {
        "key": "pb_ratio",
        "extract": lambda row, market: {
            "book_value_per_share": _ensure_float(row.get("book_value_per_share")),
            "current_price": market.get("current_price", 0),
        },
        "guard": lambda vals: vals["book_value_per_share"] != 0 and vals["current_price"],
        "compute": lambda vals: vals["current_price"] / vals["book_value_per_share"],
        "interpret": get_pb_interpretation,
    },
    "roe": {
        "key": "roe",
        "extract": lambda row, market: {
            "net_profit": _ensure_float(row.get("net_profit")),
            "total_equity": _ensure_float(row.get("equity")),
        },
        "guard": lambda vals: vals["total_equity"] != 0,
        "compute": lambda vals: (vals["net_profit"] / vals["total_equity"]) * 100,
        "interpret": get_roe_interpretation,
    },
    "eps": {
        "key": "eps",
        "extract": lambda row, market: {
            "net_profit": _ensure_float(row.get("net_profit")),
            "shares_outstanding": _ensure_float(row.get("shares_outstanding")),
        },
        "guard": lambda vals: vals["shares_outstanding"] != 0,
        "compute": lambda vals: vals["net_profit"] / vals["shares_outstanding"],
        "interpret": get_eps_interpretation,
    },
    "current_ratio": {
        "key": "current_ratio",
        "extract": lambda row, market: {
            "current_assets": _ensure_float(row.get("current_assets")),
            "current_liabilities": _ensure_float(row.get("current_liabilities")),
        },
        "guard": lambda vals: vals["current_liabilities"] != 0,
        "compute": lambda vals: vals["current_assets"] / vals["current_liabilities"],
        "interpret": get_current_ratio_interpretation,
    },
    "debt_to_equity": {
        "key": "debt_to_equity",
        "extract": lambda row, market: {
            "total_liabilities": _ensure_float(row.get("total_liabilities")),
            "total_equity": _ensure_float(row.get("equity")),
        },
        "guard": lambda vals: vals["total_equity"] != 0,
        "compute": lambda vals: vals["total_liabilities"] / vals["total_equity"],
        "interpret": get_debt_to_equity_interpretation,
    },
    "profit_margin": {
        "key": "profit_margin",
        "extract": lambda row, market: {
            "net_profit": _ensure_float(row.get("net_profit")),
            "revenue": _ensure_float(row.get("revenue")),
        },
        "guard": lambda vals: vals["revenue"] != 0,
        "compute": lambda vals: (vals["net_profit"] / vals["revenue"]) * 100,
        "interpret": get_profit_margin_interpretation,
    },
    "quick_ratio": {
        "key": "quick_ratio",
        "extract": lambda row, market: {
            "quick_assets": _ensure_float(row.get("cash_and_equivalents")) + _ensure_float(row.get("marketable_securities")),
            "current_liabilities": _ensure_float(row.get("current_liabilities")),
        },
        "guard": lambda vals: vals["current_liabilities"] != 0,
        "compute": lambda vals: vals["quick_assets"] / vals["current_liabilities"],
        "interpret": get_quick_ratio_interpretation,
    },
    "asset_turnover": {
        "key": "asset_turnover",
        "extract": lambda row, market: {
            "revenue": _ensure_float(row.get("revenue")),
            "total_assets": _ensure_float(row.get("total_assets")),
        },
        "guard": lambda vals: vals["total_assets"] != 0,
        "compute": lambda vals: vals["revenue"] / vals["total_assets"],
        "interpret": get_asset_turnover_interpretation,
    },
    "dividend_yield": {
        "key": "dividend_yield",
        "extract": lambda row, market: {
            "dividend_per_share": _ensure_float(row.get("dividend_per_share")),
            "current_price": market.get("current_price", 0),
        },
        "guard": lambda vals: vals["current_price"] != 0,
        "compute": lambda vals: (vals["dividend_per_share"] / vals["current_price"]) * 100,
        "interpret": get_dividend_yield_interpretation,
    },
}


_RATIO_FRAME_ALIASES: dict[str, list[str]] = {
    "pe": ["price to earning", "price_to_earning", "p/e", "pricetoearning"],
    "pb": ["price to book", "price_to_book", "p/b", "pricetobook"],
    "roe": ["return on equity", "return_on_equity", "roe"],
    "eps": ["earning per share", "earning_per_share", "eps"],
    "current_ratio": ["current ratio", "current_ratio", "thanh toan hien hanh"],
    "debt_to_equity": ["debt to equity", "debt_to_equity", "debt equity", "d/e"],
    "profit_margin": ["net profit margin", "profit margin", "profit_margin", "bien loi nhuan"],
    "quick_ratio": ["quick ratio", "quick_ratio"],
    "asset_turnover": ["asset turnover", "asset_turnover", "vong quay tai san"],
    "dividend_yield": ["dividend yield", "dividend_yield", "ty suat co tuc"],
}

_INTERPRET: dict[str, Any] = {
    "pe": get_pe_interpretation,
    "pb": get_pb_interpretation,
    "roe": get_roe_interpretation,
    "eps": get_eps_interpretation,
    "current_ratio": get_current_ratio_interpretation,
    "debt_to_equity": get_debt_to_equity_interpretation,
    "profit_margin": get_profit_margin_interpretation,
    "quick_ratio": get_quick_ratio_interpretation,
    "asset_turnover": get_asset_turnover_interpretation,
    "dividend_yield": get_dividend_yield_interpretation,
}

_FRAME_META_COLS = {"item", "item_en", "item_id", "unit", "levels", "row_number", "ticker", "quarter", "year"}


def parse_ratio_frame(frame: Any) -> tuple[dict[str, float], str | None]:
    """Parse a Finance.ratio() frame (KBS item-rows shape) to canonical fields.

    Returns (values, latest_period). Unknown shapes yield ({}, None) so
    callers fall back to the legacy balance-sheet compute path.
    """
    try:
        if frame is None or getattr(frame, "empty", False):
            return {}, None
        columns = [str(c) for c in getattr(frame, "columns", [])]
        if not columns:
            return {}, None
        item_cols = [c for c in ("item", "item_en", "item_id") if c in columns]
        period_cols = [c for c in columns if c not in _FRAME_META_COLS]
        if not item_cols or not period_cols:
            return {}, None
        latest = sorted(period_cols)[-1]
        values: dict[str, float] = {}
        for _, row in frame.iterrows():
            try:
                text = " ".join(str(row.get(c, "")) for c in item_cols).lower().replace("_", " ")
            except Exception:
                continue
            for field, aliases in _RATIO_FRAME_ALIASES.items():
                if field in values:
                    continue
                if any(a in text for a in aliases):
                    try:
                        v = float(row.get(latest))
                    except (TypeError, ValueError):
                        continue
                    if v == v:  # skip NaN
                        values[field] = v
        return values, latest
    except Exception:
        return {}, None


def _snapshot_entry(field: str, value: float, period: str | None, freshness: dict[str, Any]) -> dict[str, Any]:
    interpret = _INTERPRET.get(field)
    if interpret is None:
        return {}
    out = {
        field: {
            "value": value,
            "interpretation": interpret(value),
            "time_range": period or "Latest",
            "source": "db",
        },
    }
    out.update(freshness)
    return out


def get_financial_ratios(
    port: FinancialPort, ticker: str, ratio_type: str | None = None, parsed: dict[str, Any] | None = None, cache: CachePort | None = None
) -> dict[str, Any]:
    """Lấy các chỉ số tài chính cho một mã chứng khoán — strict via FinancialPort."""
    try:
        financial_data = port.get_financial_statement(ticker)
        if financial_data is None or getattr(financial_data, "empty", False):
            return {"error": "No financial data available"}
        # New path: Finance.ratio() frame already carries computed ratios.
        frame_vals, frame_period = parse_ratio_frame(financial_data)
        if frame_vals:
            wanted = [ratio_type] if ratio_type else list(frame_vals)
            ratios: dict[str, Any] = {}
            for name in wanted:
                if name in frame_vals and name in _INTERPRET:
                    ratios[name] = {
                        "value": frame_vals[name],
                        "interpretation": _INTERPRET[name](frame_vals[name]),
                        "time_range": frame_period or "Latest",
                        "source": "vnstock",
                    }
            if ratios:
                return ratios
            return {"error": "No ratios calculated"}
        market_data = port.get_market_data(ticker)

        ratios = {}

        row = financial_data.iloc[0].to_dict() if not financial_data.empty else {}

        # time_range is metadata only; financial statements are point-in-time
        time_range = "Latest"

        for rt_name, cfg in _RATIO_ENTRIES.items():
            if ratio_type is None or ratio_type == rt_name:
                vals = cfg["extract"](row, market_data)
                if cfg["guard"](vals):
                    result = cfg["compute"](vals)
                    ratios[cfg["key"]] = {
                        "value": result,
                        **vals,
                        "interpretation": cfg["interpret"](result),
                        "time_range": time_range,
                    }

        result = ratios if ratios else {"error": "No ratios calculated"}
        return result

    except Exception as e:
        return {"error": str(e)}

def handle_financial_ratio_query(tickers: list[str],
    field: str = "pe",) -> dict[str, Any]:
    from shared.service_helpers import call_service
    return call_service("financial_ratio", tickers=tickers, field=field)

