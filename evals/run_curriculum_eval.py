"""Evaluate ONE learning track. Semantic rubrics require independent human review.

Default: personal_finance. --validate-only needs no LLM/network.
Live runs record tool calls, chart values, errors and latency, NOT a pedagogy score.
"""

import argparse
import json
import math
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from application.learning.policy import LearningContext, catalog  # noqa: E402 - script path setup


def load_cases(track: str) -> list[dict]:
    path = ROOT / "evals/curriculum/v2" / f"{track}.jsonl"
    rows = [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    ids = set()
    for row in rows:
        if row["id"] in ids or row["track"] != track:
            raise ValueError(f"Duplicate ID or wrong track: {row['id']}")
        ids.add(row["id"])
        scope = LearningContext(track=track, lesson_id=row["lesson_id"])
        if not set(row["required_tools"]).issubset(scope.tools):
            raise ValueError(f"Required tools exceed lesson scope: {row['id']}")
        if not row["query"].strip() or not row["rubric"]:
            raise ValueError(f"Missing query/rubric: {row['id']}")
    expected = {
        lesson["id"]
        for item in catalog()["tracks"]
        if item["id"] == track
        for module in item["modules"]
        for lesson in module["lessons"]
    }
    if {row["lesson_id"] for row in rows} != expected:
        raise ValueError("Dataset does not cover every lesson in its track")
    return rows


def check_run(  # noqa: PLR0917 - explicit evaluation inputs
    case: dict,
    answer: str,
    calls: list[dict],
    charts: list[dict],
    errors: list[str],
    attempts: list[dict] | None = None,
) -> dict:
    scope = LearningContext(track=case["track"], lesson_id=case["lesson_id"])
    used = {call["name"] for call in calls}
    requested = {call["name"] for call in (attempts if attempts is not None else calls)}
    checks = {
        "has_answer": bool(answer.strip()),
        "no_stream_error": not errors,
        "no_tool_error": not any("TOOL_ERR#" in call.get("result_preview", "") for call in calls),
        "tools_within_scope": used.issubset(scope.tools),
        "requested_tools_within_scope": requested.issubset(scope.tools),
        "required_tools": set(case["required_tools"]).issubset(used),
        "forbidden_tools_absent": not (used | requested).intersection(
            case.get("forbidden_tools", [])
        ),
        "required_charts": len(charts) >= case.get("min_charts", 1 if case["expect_chart"] else 0),
    }
    for index, expected in enumerate(case.get("chart_checks", [])):
        values = [
            row.get(expected["field"])
            for chart in charts
            for row in chart["data"]
            if all(row.get(key) == value for key, value in expected["where"].items())
        ]
        checks[f"chart_value_{index + 1}"] = any(
            isinstance(value, (float, int))
            and math.isfinite(value)
            and abs(value - expected["expected"]) <= expected["tolerance"]
            for value in values
        )
    return checks


def run_case(agent, case: dict) -> dict:
    from application.agents.agent import AgentStreamEvent
    from domain.entities.chart_spec import ChartSpec

    calls, charts, errors, answer, attempts = [], [], [], [], []
    original = agent.tool_node.execute_one
    original_invoke = agent._invoke_llm

    def record_attempts(*args, **kwargs):
        response, error = original_invoke(*args, **kwargs)
        if response is not None:
            attempts.extend(
                {"name": call["name"], "args": call.get("args", {})}
                for call in (response.tool_calls or [])
            )
        return response, error

    def record(call, history, cache, retries):
        entry = {"name": call["name"], "args": call.get("args", {})}
        calls.append(entry)
        result = original(call, history, cache, retries)
        entry["result_preview"] = str(result)[:6000]
        return result

    # This runner is deliberately sequential; never patch a serving agent.
    agent.tool_node.execute_one = record
    agent._invoke_llm = record_attempts
    request_id = f"curriculum-{uuid.uuid4()}"
    started = time.monotonic()
    try:
        for event in agent.run_stream(
            case["query"],
            request_id=request_id,
            user_id=request_id,
            learning_context={"track": case["track"], "lesson_id": case["lesson_id"]},
        ):
            if isinstance(event, AgentStreamEvent):
                if event.event == "chart_spec":
                    charts.append(ChartSpec.model_validate_json(event.data).model_dump(mode="json"))
                else:
                    errors.append(event.data)
            elif event:
                answer.append(event)
    except Exception as exc:
        errors.append(f"{type(exc).__name__}: {exc}")
    finally:
        agent.tool_node.execute_one = original
        agent._invoke_llm = original_invoke
    text = "".join(answer)
    checks = check_run(case, text, calls, charts, errors, attempts)
    return {
        "id": case["id"],
        "request_id": request_id,
        "track": case["track"],
        "lesson_id": case["lesson_id"],
        "query": case["query"],
        "answer": text,
        "tool_calls": calls,
        "attempted_tool_calls": attempts,
        "charts": charts,
        "errors": errors,
        "latency_ms": round((time.monotonic() - started) * 1000),
        "automated_checks": checks,
        "automated_pass": all(checks.values()),
        "semantic_review": {"status": "pending", "rubric": case["rubric"], "scores": None},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--track", choices=["personal_finance", "market_literacy"], default="personal_finance"
    )
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--ids", nargs="+")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    cases = load_cases(args.track)
    if args.validate_only:
        print(
            f"{args.track}: {len(cases)} cases, complete lesson coverage; schema validated (no model run)."
        )
        return 0
    if args.ids:
        selected = set(args.ids)
        if selected - {case["id"] for case in cases}:
            parser.error("Unknown case ID")
        cases = [case for case in cases if case["id"] in selected]
    if args.limit is not None:
        if args.limit < 1:
            parser.error("--limit must be positive")
        cases = cases[: args.limit]
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    from application.agents.agent import StockAgent
    from infrastructure.dependencies import init_deps, shutdown_deps
    from infrastructure.observability.tracing import init_tracing

    init_tracing()
    results = []
    path = (
        args.output
        or ROOT
        / "evals/reports"
        / f"curriculum-{args.track}-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)

    def save_report(status):
        report = {
            "schema_version": "2.0",
            "track": args.track,
            "status": status,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "cases": results,
            "summary": {
                "selected": len(cases),
                "count": len(results),
                "automated_passes": sum(row["automated_pass"] for row in results),
                "semantic_reviews_pending": len(results),
                "combined_track_score": None,
            },
        }
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    save_report("running")
    try:
        init_deps()
        agent = StockAgent()
        for case in cases:
            print(f"Running {case['id']}", flush=True)
            results.append(run_case(agent, case))
            save_report("running")
    finally:
        save_report("completed" if len(results) == len(cases) else "incomplete")
        shutdown_deps()
    print(f"Report: {path}; semantic review pending.")
    return 0 if all(row["automated_pass"] for row in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
