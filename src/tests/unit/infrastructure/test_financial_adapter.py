"""RED: FinancialAdapter must use Finance.ratio() (vnstock 3.5.1).

Company.financial_statement()/market_data() do not exist on 3.5.1 —
every ratio call AttributeErrors. Correct class is Finance with
VCI -> KBS fallback, never raising (empty frame on total failure).
"""

import pandas as pd

from infrastructure.adapters.financial_adapter import FinancialAdapter


class _FakeFinance:
    instances: list = []
    calls: list = []
    mode = "ok"  # ok | boom

    def __init__(self, source, symbol, **kwargs):
        _FakeFinance.instances.append((source, symbol))
        self._source = source
        self._symbol = symbol

    def ratio(self, **kwargs):
        _FakeFinance.calls.append(self._source)
        if _FakeFinance.mode == "boom":
            raise ConnectionError("upstream down")
        if self._source == "KBS":
            raise ConnectionError("stale primary")
        return pd.DataFrame({
            "item": ["P/E", "ROE"],
            "item_en": ["Price to Earning", "Return on Equity"],
            "item_id": ["price_to_earning", "roe"],
            "2024": [15.5, 18.2],
        })


def test_adapter_uses_finance_ratio_not_company(monkeypatch):
    import vnstock.api.financial as fin_mod

    _FakeFinance.instances.clear()
    _FakeFinance.calls.clear()
    _FakeFinance.mode = "ok"
    monkeypatch.setattr(fin_mod, "Finance", _FakeFinance)

    out = FinancialAdapter().get_financial_statement("VCB")
    assert not getattr(out, "empty", True)
    # KBS tried first, VCI fallback succeeds
    assert _FakeFinance.calls[0] == "KBS"
    assert "VCI" in _FakeFinance.calls


def test_adapter_total_failure_returns_empty_frame(monkeypatch):
    import vnstock.api.financial as fin_mod

    _FakeFinance.calls.clear()
    _FakeFinance.mode = "boom"
    monkeypatch.setattr(fin_mod, "Finance", _FakeFinance)

    out = FinancialAdapter().get_financial_statement("VCB")
    assert getattr(out, "empty", False)
