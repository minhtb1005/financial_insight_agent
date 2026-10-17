"""RED: service parses Finance.ratio() frames (KBS item-rows shape)."""

import pandas as pd

from application.services.financial.financial_ratio_service import (
    parse_ratio_frame,
)


def _kbs_frame():
    return pd.DataFrame(
        {
            "item": ["P/E", "ROE", "EPS (VND)"],
            "item_en": ["Price to Earning", "Return on Equity", "Earning Per Share"],
            "item_id": ["price_to_earning", "roe", "earning_per_share"],
            "2023": [15.5, 18.2, 2500.0],
            "2024": [12.0, 20.1, 3100.0],
        }
    )


def test_parse_ratio_frame_latest_period():
    vals, period = parse_ratio_frame(_kbs_frame())
    assert period == "2024"
    assert vals["pe"] == 12.0
    assert vals["roe"] == 20.1
    assert vals["eps"] == 3100.0


def test_parse_ratio_frame_empty():
    vals, period = parse_ratio_frame(pd.DataFrame())
    assert vals == {} and period is None
