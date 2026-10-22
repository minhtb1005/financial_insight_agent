"""Retriever — search_knowledge for agent tool-calling."""

from __future__ import annotations

from typing import Any

from application.learning.references import references_for, reviewed_payload
from infrastructure.observability import get_logger
from .embedder import embed_query
from .vector_store import ALIAS, search as vs_search

logger = get_logger("rag.retriever")

_SAFETY_KEYWORDS = ["mua ngay", "bán ngay", "khuyến nghị mua", "khuyến nghị bán", "all-in"]


def _format_citation(payload: dict[str, Any], score: float | None) -> str:
    title = payload.get("title", payload.get("source_id", ""))
    url = payload.get("source_url", "")
    priority = payload.get("priority", 5)
    if payload.get("kind") == "editorial_summary":
        urls = " | ".join(payload.get("source_urls", [url]))
        return (
            f"[Nguồn đối chiếu: {title} | tóm tắt biên tập {payload['reviewed_at']} | {urls}]\n"
            + payload.get("text", "")
        )
    text = payload.get("text", "")[:600]
    return f"[Nguồn: {title} | priority={priority} | score={score:.3f} | {url}]\n{text}"


def search_knowledge(query: str, top_k: int = 5, min_score: float = 0.3) -> dict[str, Any]:
    """Search RAG knowledge base. Returns dict with hits and formatted context."""
    # Reviewed, explicitly labelled summaries stay available without an embedder.
    # Stale chunks for these source IDs must never reintroduce an old seed.
    reviewed = [{"score": None, "payload": ref.payload()} for ref in references_for(query)]
    retrieval_error = None
    hits = []
    try:
        vec = embed_query(query)
        hits = vs_search(ALIAS, vec, top_k=top_k)
    except Exception as e:
        logger.warning("retriever search failed (alias %s): %s", ALIAS, e)
        retrieval_error = str(e)

    # filter by score and rerank by priority (lower priority number = higher trust)
    filtered = [h for h in hits if (h.get("score") or 0) >= min_score]
    # sort by priority then score descending
    filtered.sort(key=lambda h: (h.get("payload", {}).get("priority", 99), -(h.get("score") or 0)))

    selected = reviewed[:top_k]
    seen = {hit["payload"]["source_id"] for hit in selected}
    for hit in filtered:
        payload = hit.get("payload", {})
        source_id = payload.get("source_id")
        replacement = reviewed_payload(source_id)
        selected_hit = hit
        if replacement:
            if source_id in seen:
                continue
            selected_hit = {"score": None, "payload": replacement}
            seen.add(source_id)
        selected.append(selected_hit)
        if len(selected) >= top_k:
            break
    selected = selected[:top_k]
    out = {
        "hits": selected,
        "context": "\n\n---\n\n".join(
            _format_citation(hit["payload"], hit.get("score")) for hit in selected
        ),
        "count": len(selected),
    }
    if retrieval_error:
        out["retrieval_error" if selected else "error"] = retrieval_error
    return out


def is_disallowed_advice(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in _SAFETY_KEYWORDS)
