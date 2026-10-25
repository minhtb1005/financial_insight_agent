import json
import math
from unittest.mock import patch

import pytest

from application.services.dashboard.spec_validator import validate_chart_spec
from mcp_server.tools.learning_chart import generate_learning_chart
from mcp_server.tools.visualize import _fetch_rows, generate_chart_spec


def test_budget_values_conserve_income_and_never_use_market_service():
    with patch(
        "mcp_server.tools.visualize.handle_price_query",
        side_effect=AssertionError("market accessed"),
    ):
        payload = json.loads(generate_learning_chart("budget", 12_000_000))
    spec = payload["spec"]
    assert validate_chart_spec(spec).valid
    assert [row["value"] for row in spec["data"]] == [6_000_000, 3_600_000, 2_400_000]
    assert spec["data_source"].startswith("calculator:budget:")


def test_purchasing_power_matches_independent_formula_and_has_two_series():
    spec = json.loads(generate_learning_chart("purchasing_power", 100_000_000, 5, 6, 4))["spec"]
    assert validate_chart_spec(spec).valid
    final = {row["symbol"]: row["value"] for row in spec["data"] if row["year"] == 5}
    assert final["Danh nghĩa"] == pytest.approx(100_000_000 * 1.06**5, abs=1)
    assert final["Sức mua hiện tại"] == pytest.approx(100_000_000 * (1.06 / 1.04) ** 5, abs=1)
    assert "giả định" in spec["title"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"amount": -1},
        {"amount": math.nan},
        {"amount": math.inf},
        {"years": 0},
        {"years": 51},
        {"inflation_pct": -100},
    ],
)
def test_invalid_scenarios_return_error_not_chart(kwargs):
    assert generate_learning_chart("purchasing_power", **({"amount": 100} | kwargs)).startswith(
        "TOOL_ERR#VALIDATION"
    )


def test_stock_chart_requires_symbol_and_does_not_substitute_metrics():
    with patch("mcp_server.tools.visualize.handle_price_query") as service:
        assert generate_chart_spec("Vẽ giá", symbols=None).startswith("TOOL_ERR#VALIDATION")
        with pytest.raises(ValueError, match="OHLC"):
            _fetch_rows(["VNM"], "pe", 6, None)
        service.assert_not_called()


def test_stock_chart_fetches_full_ohlcv_and_preserves_volume():
    data = {
        "VNM": {
            "data": [
                {
                    "date": "2024-01-02",
                    "open_price": 5,
                    "high": 7,
                    "low": 4,
                    "close": 6,
                    "volume": 1000,
                }
            ]
        }
    }
    with patch("mcp_server.tools.visualize.handle_price_query", return_value=data) as service:
        rows, _ = _fetch_rows(["VNM"], "volume", 6, None)
    assert service.call_args.kwargs["field"] == "ohlcv"
    assert rows[0]["volume"] == 1000
