import importlib.util
from pathlib import Path

from infrastructure.guardrails.query_validator import QuerySizeLimit, TickerValidator

ROOT = Path(__file__).resolve().parents[4]
spec = importlib.util.spec_from_file_location(
    "curriculum_eval", ROOT / "evals/run_curriculum_eval.py"
)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def test_both_datasets_cover_all_lessons_and_natural_queries_pass_ticker_validation():
    primary = runner.load_cases("personal_finance")
    optional = runner.load_cases("market_literacy")
    assert len(primary) == 68
    assert len(optional) == 14
    for case in primary + optional:
        assert QuerySizeLimit().validate(case["query"], "test").passed, case["id"]
        assert TickerValidator().validate(case["query"], "test").passed, case["id"]


def test_evaluator_detects_wrong_tool_and_incorrect_chart_value():
    case = next(
        row for row in runner.load_cases("personal_finance") if row["id"].endswith(":budget_chart")
    )
    checks = runner.check_run(
        case,
        "Example",
        [{"name": "get_stock_price"}],
        [{"data": [{"category": "Thiết yếu", "value": 7_000_000}]}],
        [],
    )
    assert not checks["tools_within_scope"]
    assert not checks["required_tools"]
    assert not checks["chart_value_1"]


def test_correct_chart_checks_do_not_claim_semantic_quality():
    case = next(
        row for row in runner.load_cases("personal_finance") if row["id"].endswith(":budget_chart")
    )
    charts = [
        {
            "data": [
                {"category": label, "value": value}
                for label, value in (
                    ("Thiết yếu", 6000000),
                    ("Mong muốn", 3600000),
                    ("Tiết kiệm", 2400000),
                )
            ]
        }
    ]
    checks = runner.check_run(
        case, "Present but not graded", [{"name": "generate_learning_chart"}], charts, []
    )
    assert all(checks.values())
    assert case["review_status"] == "pending"


def test_blocked_tool_selection_still_fails_scope_check():
    case = runner.load_cases("personal_finance")[0]
    checks = runner.check_run(
        case,
        "Answer after the invalid tool was blocked",
        [],
        [],
        [],
        attempts=[{"name": "get_stock_price"}],
    )
    assert checks["tools_within_scope"]
    assert not checks["requested_tools_within_scope"]


def test_tool_transport_error_does_not_pass_as_successful_teaching():
    case = runner.load_cases("personal_finance")[0]
    checks = runner.check_run(
        case,
        "An answer despite failed tools",
        [
            {
                "name": "budget_template",
                "result_preview": "TOOL_ERR#UNKNOWN StructuredTool does not support sync invocation.",
            }
        ],
        [],
        [],
    )
    assert not checks["no_tool_error"]
