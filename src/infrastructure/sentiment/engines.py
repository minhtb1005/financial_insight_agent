"""Article sentiment engines with a uniform verdict interface (Phase 3).

- ``keyword``: maps a lexicon score float to a label (lexicon itself lives in
  the application service — no layering inversion).
- ``hf``: PhoBERT-family classifier (default ``Marky12345/BigData_2026``,
  labels Bullish/Bearish/Uncertainty), lazy-loaded, CPU-friendly.
- ``llm``: ``gpt-4o-mini`` zero-shot with rubric via structured output.

Every engine returns ``{"label", "score", "rationale", "engine"}`` with
``label`` in {pos, neu, neg} and ``score`` in [-1, 1].  ``classify_article``
dispatches by name with keyword fallback on any failure (never raises for a
single article — the tool path must stay resilient).
"""

from __future__ import annotations

import logging
from typing import Any, Literal

logger = logging.getLogger(__name__)

Label = Literal["pos", "neu", "neg"]

HF_MODEL_ID = "Marky12345/BigData_2026"
HF_LABELS = ("Bullish", "Bearish", "Uncertainty")
HF2GOLD: dict[str, Label] = {"Bullish": "pos", "Bearish": "neg", "Uncertainty": "neu"}

_hf_pipe: Any = None


def classify_keyword(score: float) -> dict[str, Any]:
    """Map a lexicon score float to a verdict (fallback engine, zero cost)."""
    label: Label = "pos" if score > 0 else ("neg" if score < 0 else "neu")
    return {
        "label": label,
        "score": round(float(score), 4),
        "rationale": "keyword lexicon match",
        "engine": "keyword",
    }


def classify_llm(title: str, excerpt: str = "", provider: Any | None = None) -> dict[str, Any]:
    """Zero-shot LLM verdict via structured output (gpt-4o-mini)."""
    from pydantic import BaseModel, Field

    from infrastructure.llm.llm_provider import LLMProvider

    class SentimentVerdict(BaseModel):
        label: Label = Field(description="pos=tích cực, neu=trung tính, neg=tiêu cực")
        score: float = Field(description="Điểm cảm xúc trong [-1, 1]", ge=-1.0, le=1.0)
        rationale: str = Field(description="Lý do 1 câu tiếng Việt")

    provider = provider or LLMProvider()
    # fallback=True builds the primary->fallback chain (primary gpt-4o-mini
    # first). NOTE: with fallback=False the provider returns the Groq model
    # first, whose key in this env is invalid — do not rely on the default.
    llm = provider.with_structured_output(SentimentVerdict, fallback=True)
    prompt = (
        "Bạn là chuyên gia phân tích tâm lý thị trường chứng khoán Việt Nam. "
        "Đọc tiêu đề + trích đoạn tin dưới đây và gán nhãn cảm xúc ĐỐI VỚI MÃ CỔ PHIẾU được nhắc tới.\n"
        "Rubric: pos = tin tốt cho giá (lãi tăng, trúng thầu, cổ tức, nâng hạng...); "
        "neg = tin xấu (lỗ, phạt, kiện tụng, hạ hạng, nợ xấu...); "
        "neu = trung tính/thuần thông tin (lịch sự kiện, số liệu không hàm ý...). "
        "Cẩn thận phủ định (VD 'không tăng trưởng' là neg). Trả về đúng schema.\n\n"
        f"Tiêu đề: {title}\nTrích đoạn: {excerpt[:800]}\n\n"
        # NOTE: OpenAI json_mode rejects requests whose messages lack the word
        # "json" — the sentence below is load-bearing, do not remove it.
        "Trả về đúng JSON schema với 3 trường label/score/rationale."
    )
    verdict = llm.invoke(prompt)
    return {
        "label": verdict.label,
        "score": round(float(verdict.score), 4),
        "rationale": verdict.rationale,
        "engine": "llm",
    }


def classify_hf(title: str, excerpt: str = "", model_id: str = HF_MODEL_ID) -> dict[str, Any]:
    """PhoBERT-family classifier verdict (local, free, ~300ms CPU/article)."""
    global _hf_pipe
    if _hf_pipe is None:
        from transformers import pipeline

        _hf_pipe = pipeline("text-classification", model=model_id, top_k=None)
    text = f"{title} {excerpt}"[:512]
    preds = _hf_pipe(text)[0]
    best = max(preds, key=lambda p: p["score"])
    label = HF2GOLD.get(best["label"], "neu")
    signed = best["score"] if label == "pos" else (-best["score"] if label == "neg" else 0.0)
    detail = ", ".join(f"{p['label']}={p['score']:.2f}" for p in preds)
    return {
        "label": label,
        "score": round(float(signed), 4),
        "rationale": f"HF {best['label']} p={best['score']:.2f} [{detail}]",
        "engine": "hf",
    }


def classify_article(
    title: str,
    excerpt: str = "",
    engine: str = "hf",
    keyword_score: float | None = None,
    provider: Any | None = None,
) -> dict[str, Any]:
    """Dispatch to an engine with keyword fallback (never raises)."""
    try:
        if engine == "llm":
            return classify_llm(title, excerpt, provider=provider)
        if engine == "hf":
            return classify_hf(title, excerpt)
    except Exception as e:
        logger.warning("Sentiment engine %s failed, keyword fallback: %s", engine, e)
    if keyword_score is None:
        keyword_score = 0.0
    return classify_keyword(keyword_score)
