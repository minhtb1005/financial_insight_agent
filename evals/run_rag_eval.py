"""RAG benchmark runner for the `search_knowledge` tool (Phase 2).

Pipeline per case:
  1. Retrieve with the REAL `search_knowledge` path (Qdrant + OpenAI embeddings).
  2. Score Retrieval Precision@k / Recall@k / hit-rate vs hand labels in
     evals/golden/rag_dataset.jsonl (chunk_hash identity).
  3. Answer with the baseline chat model grounded ONLY on retrieved context,
     with strict [source:chunkprefix] citations (or a fixed refusal sentence).
  4. Score citation correctness (citation must resolve to a retrieved chunk),
     refusal rate (out-of-scope), and answer key-phrase coverage.

Usage::

    python evals/run_rag_eval.py --limit 4            # smoke (retrieval + answer)
    python evals/run_rag_eval.py --skip-answer         # retrieval only, no LLM cost
    python evals/run_rag_eval.py                       # full baseline
    python evals/run_rag_eval.py --ids rag_vbpl_001 rag_tt_001
    python evals/run_rag_eval.py --qdrant-path data/qdrant_local_v117

Env: NVIDIA_API_KEY* + NVIDIA_CHAT_MODEL (default nvidia/nemotron-3-ultra-550b-a55b) from .env.
Qdrant is resolved exactly like production (QDRANT_PATH > QDRANT_URL >
host/port); --qdrant-path only overrides the env var for this process.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "evals"))

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

DEFAULT_DATASET = ROOT / "evals" / "golden" / "rag_dataset.jsonl"
REPORTS_DIR = ROOT / "evals" / "reports"

ANSWER_SYSTEM = (
    "Bạn là trợ lý tài chính. Chỉ được trả lời DỰA TRÊN các đoạn ngữ cảnh được "
    "cung cấp dưới đây. Mỗi khẳng định thực tế phải kèm trích dẫn dạng "
    "[source_id:8 ký tự đầu của chunk_hash] (ví dụ [vbpl_24_2025:bca88e90]). "
    "Chỉ dùng các source_id và chunk_hash xuất hiện trong ngữ cảnh, không bịa thêm. "
    "Nếu ngữ cảnh không đủ để trả lời, hãy chỉ trả lời đúng một câu: "
    "'{refusal}'"
)


def load_cases(dataset: Path, ids: list[str] | None, limit: int | None) -> list[dict]:
    cases = [
        json.loads(ln)
        for ln in dataset.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    if ids:
        wanted = set(ids)
        cases = [c for c in cases if c["id"] in wanted]
    if limit:
        cases = cases[:limit]
    return cases


def retrieved_keys(hits: list[dict]) -> tuple[list[str], list[str]]:
    """Return (chunk_hash list, source_id list) for retrieved hits."""
    hashes, sources = [], []
    for h in hits:
        payload = (h or {}).get("payload", {}) or {}
        ch = payload.get("chunk_hash")
        if not ch:
            ch = "%s#%s" % (payload.get("source_id", "?"), payload.get("chunk_index", "?"))
        hashes.append(ch)
        sources.append(payload.get("source_id", "?"))
    return hashes, sources


def build_context(hits: list[dict], hashes: list[str]) -> str:
    blocks = []
    for h, key in zip(hits, hashes):
        payload = (h or {}).get("payload", {}) or {}
        short = key[:8] if len(key) >= 8 else key
        blocks.append(
            "[%s:%s] %s" % (payload.get("source_id", "?"), short, (payload.get("text", "") or "")[:1200])
        )
    return "\n\n---\n\n".join(blocks)


def generate_answer(client, model: str, query: str, context: str, refusal: str) -> tuple[str, float | None]:
    t0 = time.time()
    try:
        resp = client.chat.completions.create(
            model=model,
            temperature=0,
            max_tokens=600,
            messages=[
                {"role": "system", "content": ANSWER_SYSTEM.format(refusal=refusal)},
                {"role": "user", "content": "Ngữ cảnh:\n%s\n\nCâu hỏi: %s" % (context or "(không có ngữ cảnh)", query)},
            ],
        )
        return resp.choices[0].message.content or "", round((time.time() - t0) * 1000, 2)
    except Exception as exc:  # network/LLM failure must not kill the whole run
        return "(answer error: %s: %s)" % (type(exc).__name__, exc), None


def run_case(search_fn, client, model: str, case: dict, top_k: int, min_score: float,
             skip_answer: bool, refusal: str) -> dict:
    from rag_metrics import (
        answer_contains_rate,
        citation_correctness,
        extract_citations,
        hit_rate_at_k,
        is_refusal,
        precision_at_k,
        recall_at_k,
    )

    t0 = time.time()
    try:
        res = search_fn(case["query"], top_k=top_k, min_score=min_score)
        hits = res.get("hits", [])
        error = res.get("error")
    except Exception as exc:
        hits, error = [], "%s: %s" % (type(exc).__name__, exc)
    latency_ms = round((time.time() - t0) * 1000, 2)

    hashes, sources = retrieved_keys(hits)
    expected = set(case.get("expected_chunks", []))
    retrieval = {
        "p_at_k": precision_at_k(hashes, expected, top_k),
        "r_at_k": recall_at_k(hashes, expected, top_k),
        "hit": hit_rate_at_k(hashes, expected, top_k),
        "n_returned": len(hits),
        "error": error,
    }

    sample = {
        "id": case["id"], "tier": case.get("tier"), "query": case["query"],
        "expects_refusal": bool(case.get("expects_refusal", False)),
        "retrieval": retrieval,
        "retrieved": [{"chunk_hash": h, "source_id": s} for h, s in zip(hashes, sources)],
        "latency_ms": latency_ms,
    }

    if skip_answer:
        return sample

    context = build_context(hits, hashes)
    answer, ans_ms = generate_answer(client, model, case["query"], context, refusal)
    refused = is_refusal(answer)
    citations = extract_citations(answer)
    n_ok, n_tot = citation_correctness(citations, hashes, sources)
    sample.update({
        "answer": answer,
        "answer_latency_ms": ans_ms,
        "refused": refused,
        "citations": citations,
        "citation_correct": n_ok,
        "citation_total": n_tot,
        "citation_correctness": (n_ok / n_tot) if n_tot else None,
        "answer_contains_rate": answer_contains_rate(answer, case.get("expected_answer_contains", [])),
    })
    return sample


def aggregate(samples: list[dict], top_k: int) -> dict:
    from rag_metrics import mean_or_none

    in_scope = [s for s in samples if not s.get("expects_refusal")]
    oos = [s for s in samples if s.get("expects_refusal")]

    def _col(rows, *path):
        vals = []
        for r in rows:
            v = r
            for p in path:
                v = (v or {}).get(p) if isinstance(v, dict) else None
            vals.append(v)
        return vals

    # citation macro: mean of per-case correctness (cases with citations only);
    # citation micro: total correct / total citations.
    per_case_cit = [s.get("citation_correctness") for s in in_scope if "citation_correctness" in s]
    tot_ok = sum(s.get("citation_correct", 0) for s in in_scope if "citation_correct" in s)
    tot_n = sum(s.get("citation_total", 0) for s in in_scope if "citation_total" in s)

    per_tier: dict[str, dict] = {}
    for tier in sorted({s.get("tier", "?") for s in in_scope}):
        rows = [s for s in in_scope if s.get("tier") == tier]
        per_tier[tier] = {
            "n": len(rows),
            "p_at_k": mean_or_none(_col(rows, "retrieval", "p_at_k")),
            "r_at_k": mean_or_none([v for v in _col(rows, "retrieval", "r_at_k")]),
            "hit_rate": mean_or_none([v for v in _col(rows, "retrieval", "hit")]),
        }

    return {
        "n_cases": len(samples),
        "n_in_scope": len(in_scope),
        "n_out_of_scope": len(oos),
        "top_k": top_k,
        "retrieval_p_at_k": mean_or_none(_col(in_scope, "retrieval", "p_at_k")),
        "retrieval_r_at_k": mean_or_none([v for v in _col(in_scope, "retrieval", "r_at_k")]),
        "retrieval_hit_rate": mean_or_none([v for v in _col(in_scope, "retrieval", "hit")]),
        "per_tier": per_tier,
        "citation_macro": mean_or_none([v for v in per_case_cit]),
        "citation_micro": (tot_ok / tot_n) if tot_n else None,
        "citation_totals": {"correct": tot_ok, "total": tot_n},
        "refusal_rate": mean_or_none([1.0 if s.get("refused") else 0.0 for s in oos]) if oos and any("refused" in s for s in oos) else None,
        "false_refusal_rate": mean_or_none([1.0 if s.get("refused") else 0.0 for s in in_scope]) if in_scope and any("refused" in s for s in in_scope) else None,
        "answer_contains_rate": mean_or_none([v for v in _col(in_scope, "answer_contains_rate")]),
        "mean_retrieval_latency_ms": mean_or_none(_col(samples, "latency_ms")),
        "retrieval_errors": sum(1 for s in samples if (s.get("retrieval") or {}).get("error")),
    }


def write_report(run_dir: Path, agg: dict, samples: list[dict], meta: dict) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "samples.json").write_text(
        json.dumps(samples, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (run_dir / "report.json").write_text(
        json.dumps({"meta": meta, "aggregate": agg}, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8")

    def _f(v):
        return f"{v:.4f}" if isinstance(v, (int, float)) else "n/a"

    lines = [
        "# RAG Benchmark Report (search_knowledge)",
        "",
        f"- Run: `{meta['run_id']}`",
        f"- Model: `{meta['model']}` | top_k={meta['top_k']} min_score={meta['min_score']}",
        f"- Dataset: `{meta['dataset']}` ({meta['n_cases']} cases: "
        f"{agg['n_in_scope']} in-scope + {agg['n_out_of_scope']} out-of-scope)",
        f"- Qdrant: `{meta.get('qdrant_info', '?')}`",
        "",
        "## Aggregate",
        "",
        "| Metric | Score |",
        "|---|---|",
        f"| retrieval P@{agg['top_k']} | {_f(agg['retrieval_p_at_k'])} |",
        f"| retrieval R@{agg['top_k']} | {_f(agg['retrieval_r_at_k'])} |",
        f"| retrieval hit-rate | {_f(agg['retrieval_hit_rate'])} |",
        f"| citation correctness (macro) | {_f(agg['citation_macro'])} |",
        f"| citation correctness (micro) | {_f(agg['citation_micro'])} |",
        f"| refusal rate (out-of-scope) | {_f(agg['refusal_rate'])} |",
        f"| false refusal rate (in-scope) | {_f(agg['false_refusal_rate'])} |",
        f"| answer key-phrase coverage | {_f(agg['answer_contains_rate'])} |",
        "",
        "## Per-tier retrieval",
        "",
        "| Tier | n | P@k | R@k | hit-rate |",
        "|---|---|---|---|---|",
    ]
    for tier, t in agg.get("per_tier", {}).items():
        lines.append(f"| {tier} | {t['n']} | {_f(t['p_at_k'])} | {_f(t['r_at_k'])} | {_f(t['hit_rate'])} |")
    lines += ["", "## Notes",
              "- Citation correctness is strict: a citation counts only if it resolves "
              "to a chunk actually retrieved for that query.",
              "- Refusal-expected (out-of-scope) cases are excluded from retrieval/citation means.",
              "- Full per-case evidence in `samples.json`."]
    (run_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--ids", nargs="*", default=None)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--min-score", type=float, default=0.0)
    parser.add_argument("--model", default=os.getenv("NVIDIA_CHAT_MODEL", "nvidia/nemotron-3-ultra-550b-a55b"))
    parser.add_argument("--qdrant-path", default=None,
                        help="override QDRANT_PATH for this process only (no .env change)")
    parser.add_argument("--skip-answer", action="store_true",
                        help="retrieval metrics only (no chat LLM calls)")
    args = parser.parse_args()

    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=False)
    if args.qdrant_path:
        os.environ["QDRANT_PATH"] = args.qdrant_path
    model = args.model or os.getenv("NVIDIA_CHAT_MODEL", "nvidia/nemotron-3-ultra-550b-a55b")

    from rag_metrics import REFUSAL_SENTENCE

    cases = load_cases(Path(args.dataset), args.ids, args.limit)
    print(f"[rag-eval] {len(cases)} case(s) from {args.dataset}")
    if not cases:
        print("[rag-eval] FATAL: no cases matched")
        return 1

    from infrastructure.rag.retriever import search_knowledge

    client = None
    if not args.skip_answer:
        from openai import OpenAI

        if model.startswith("nvidia/"):
            from infrastructure.llm.nvidia_key_pool import NvidiaKeyPool

            pool = NvidiaKeyPool()
            if not len(pool):
                print("[rag-eval] FATAL: NVIDIA_API_KEY* missing")
                return 1
            client = OpenAI(
                base_url=os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
                api_key=pool.keys[0],
            )
        else:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                print("[rag-eval] FATAL: OPENAI_API_KEY missing")
                return 1
            client = OpenAI(api_key=api_key)

    try:
        from infrastructure.rag.vector_store import alias_target, collection_info

        target = alias_target()
        info = collection_info(target) if target else {}
        qdrant_info = "alias finsight_knowledge -> %s %s" % (target, info)
    except Exception as exc:
        qdrant_info = "unavailable: %s" % exc

    samples = []
    for i, case in enumerate(cases, start=1):
        print(f"[rag-eval] ({i}/{len(cases)}) {case['id']}: {case['query'][:56]}...")
        try:
            samples.append(run_case(search_knowledge, client, model, case,
                                    args.top_k, args.min_score, args.skip_answer,
                                    REFUSAL_SENTENCE))
        except Exception as exc:
            print(f"[rag-eval]   case FAILED: {type(exc).__name__}: {exc}")
            samples.append({"id": case["id"], "tier": case.get("tier"),
                            "query": case["query"],
                            "expects_refusal": bool(case.get("expects_refusal", False)),
                            "error": "%s: %s" % (type(exc).__name__, exc)})

    agg = aggregate(samples, args.top_k)
    run_id = "rag-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    meta = {"run_id": run_id, "model": model, "top_k": args.top_k,
            "min_score": args.min_score, "dataset": str(args.dataset),
            "n_cases": len(samples), "qdrant_info": qdrant_info,
            "skip_answer": args.skip_answer}
    run_dir = REPORTS_DIR / run_id
    write_report(run_dir, agg, samples, meta)

    print("\n[rag-eval] Aggregate:")
    for k in ("retrieval_p_at_k", "retrieval_r_at_k", "retrieval_hit_rate",
              "citation_macro", "citation_micro", "refusal_rate",
              "false_refusal_rate", "answer_contains_rate"):
        print(f"  {k}: {agg[k]}")
    print(f"[rag-eval] Report -> {run_dir / 'report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
