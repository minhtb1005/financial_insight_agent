"""Benchmark news sentiment approaches on the hand-labeled golden set.

Compares:
  (a) keyword baseline (news_sentiment_service._classify_sentiment, as-is)
  (b) HF model Marky12345/BigData_2026 as-is (CPU, transformers)
  (c) LLM gpt-4o-mini zero-shot (opt-in --with-llm, costs ~45 calls)

Label mapping: golden pos/neu/neg <-> model Bullish/Bearish/Uncertainty.
Keyword score: >0 -> pos, <0 -> neg, ==0 -> neu.

Usage: python evals/run_news_sentiment_eval.py [--skip-hf] [--with-llm]
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from application.services.portfolio.news_sentiment_service import _classify_sentiment  # noqa: E402

GOLDEN = REPO / "evals" / "golden" / "news_sentiment_labels.jsonl"
HF_ID = "Marky12345/BigData_2026"
HF_LABELS = ["Bullish", "Bearish", "Uncertainty"]
HF2GOLD = {"Bullish": "pos", "Bearish": "neg", "Uncertainty": "neu"}


def load_golden() -> list[dict]:
    rows = []
    for line in GOLDEN.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def kw_label(text: str) -> str:
    s = _classify_sentiment(text)
    return "pos" if s > 0 else ("neg" if s < 0 else "neu")


def metrics(gold: list[str], pred: list[str]) -> dict:
    labels = ["pos", "neu", "neg"]
    correct = sum(g == p for g, p in zip(gold, pred))
    acc = correct / len(gold) if gold else 0.0
    f1s = {}
    for lab in labels:
        tp = sum(g == lab and p == lab for g, p in zip(gold, pred))
        fp = sum(g != lab and p == lab for g, p in zip(gold, pred))
        fn = sum(g == lab and p != lab for g, p in zip(gold, pred))
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1s[lab] = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    macro_f1 = sum(f1s.values()) / len(f1s)
    return {"accuracy": round(acc, 4), "macro_f1": round(macro_f1, 4), "f1_per_class": {k: round(v, 4) for k, v in f1s.items()}, "n": len(gold)}


def run_keyword(rows: list[dict]) -> dict:
    gold, pred = [], []
    for r in rows:
        gold.append(r["label"])
        pred.append(kw_label(f"{r['title']} {r['excerpt']}"))
    print("keyword confusion (gold->pred):", Counter(zip(gold, pred)))
    return metrics(gold, pred)


def run_hf(rows: list[dict]) -> dict:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(HF_ID)
    model = AutoModelForSequenceClassification.from_pretrained(HF_ID)
    model.eval()
    gold, pred = [], []
    with torch.no_grad():
        for r in rows:
            text = f"{r['title']} {r['excerpt']}"[:512]
            inputs = tok(text, return_tensors="pt", truncation=True, max_length=256)
            logits = model(**inputs).logits
            lab = HF_LABELS[int(logits.argmax())]
            gold.append(r["label"])
            pred.append(HF2GOLD[lab])
    print("hf confusion (gold->pred):", Counter(zip(gold, pred)))
    return metrics(gold, pred)


def run_llm(rows: list[dict]) -> dict:
    from infrastructure.sentiment.engines import classify_llm

    gold, pred, failed = [], [], 0
    for i, r in enumerate(rows, 1):
        try:
            v = classify_llm(r["title"], r.get("excerpt", ""))
            pred.append(v["label"])
        except Exception as e:
            failed += 1
            pred.append("neu")
            print(f"  llm case {i} fallback neu: {type(e).__name__}")
        gold.append(r["label"])
        if i % 15 == 0:
            print(f"  llm progress {i}/{len(rows)}")
    print("llm confusion (gold->pred):", Counter(zip(gold, pred)), f"failed={failed}")
    out = metrics(gold, pred)
    out["failed"] = failed
    return out


def main() -> None:
    from dotenv import load_dotenv

    load_dotenv(REPO / ".env")
    rows = load_golden()
    print(f"golden n={len(rows)} dist={Counter(r['label'] for r in rows)}")
    kw = run_keyword(rows)
    print("KEYWORD as-is:", json.dumps(kw, ensure_ascii=False))
    out = {"keyword": kw}
    if "--skip-hf" not in sys.argv:
        try:
            hf = run_hf(rows)
            print("HF as-is:", json.dumps(hf, ensure_ascii=False))
            out["hf_bigdata2026"] = hf
        except Exception as e:
            print(f"HF BLOCKER: {type(e).__name__}: {str(e)[:500]}")
            out["hf_bigdata2026"] = {"blocker": f"{type(e).__name__}: {str(e)[:200]}"}
    if "--with-llm" in sys.argv:
        try:
            llm = run_llm(rows)
            print("LLM gpt-4o-mini:", json.dumps(llm, ensure_ascii=False))
            out["llm"] = llm
        except Exception as e:
            print(f"LLM BLOCKER: {type(e).__name__}: {str(e)[:500]}")
            out["llm"] = {"blocker": f"{type(e).__name__}: {str(e)[:200]}"}
    print("RESULT_JSON:" + json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
