"""Pure scoring helpers for the search_knowledge RAG benchmark.

No I/O, no network, no LLM — safe for unit tests. Convention follows
evals/metrics_duplicates.py (pure functions + tests under src/tests/unit).
"""

from __future__ import annotations

import re
import statistics

# Citations emitted by the answer prompt look like [source_id:chunkprefix]
# or a bare [source_id]. Chunk prefix must be >= 8 hex chars to count.
CITATION_RE = re.compile(r"\[([A-Za-z0-9_]+(?::[A-Za-z0-9]+)?)\]")

REFUSAL_PATTERNS = (
    "không tìm thấy thông tin",
    "không có thông tin",
    "không có trong cơ sở",
    "nằm ngoài",
    "ngoài phạm vi",
    "không thể trả lời",
    "từ chối",
    "không đủ thông tin",
    "không đủ cơ sở",
    "xin phép không trả lời",
)

REFUSAL_SENTENCE = (
    "Tôi không tìm thấy thông tin liên quan trong cơ sở tri thức "
    "nên xin phép không trả lời."
)


def normalize_text(s: str) -> str:
    """Lowercase + collapse whitespace for robust substring checks."""
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


def precision_at_k(retrieved: list[str], expected: set[str], k: int) -> float:
    """|retrieved[:k] ∩ expected| / k. Empty retrieval → 0.0."""
    if k <= 0:
        raise ValueError("k must be positive")
    if not retrieved:
        return 0.0
    hits = len(set(retrieved[:k]) & set(expected))
    return hits / k


def recall_at_k(retrieved: list[str], expected: set[str], k: int) -> float | None:
    """|retrieved[:k] ∩ expected| / |expected|. Empty expected → None (n/a)."""
    if k <= 0:
        raise ValueError("k must be positive")
    if not expected:
        return None
    if not retrieved:
        return 0.0
    hits = len(set(retrieved[:k]) & set(expected))
    return hits / len(expected)


def hit_rate_at_k(retrieved: list[str], expected: set[str], k: int) -> float | None:
    """1.0 if any expected id is in retrieved[:k], else 0.0. None if no expected."""
    if not expected:
        return None
    return 1.0 if (set(retrieved[:k]) & set(expected)) else 0.0


def extract_citations(text: str) -> list[str]:
    """Return raw citation keys in order of appearance, e.g. 'src:deadbeef'."""
    return CITATION_RE.findall(text or "")


def citation_is_correct(citation: str, retrieved_hashes: list[str], retrieved_sources: list[str]) -> bool:
    """Strict check: citation must resolve to something actually retrieved.

    Accepted forms:
      - full chunk_hash equal to a retrieved hash;
      - 'source:prefix' or bare prefix (>= 8 chars) matching the start of a
        retrieved chunk_hash;
      - bare source_id equal to a retrieved source_id.
    """
    cit = (citation or "").strip()
    if not cit:
        return False
    if ":" in cit:
        head, body = cit.split(":", 1)
        if body in retrieved_hashes:
            return True  # full chunk_hash identifies the doc regardless of source label
        return (
            head in retrieved_sources
            and len(body) >= 8
            and any(h.startswith(body) for h in retrieved_hashes if h)
        )
    if cit in retrieved_hashes:
        return True
    if cit in retrieved_sources:
        return True
    return len(cit) >= 8 and any(h.startswith(cit) for h in retrieved_hashes if h)


def citation_correctness(
    citations: list[str], retrieved_hashes: list[str], retrieved_sources: list[str]
) -> tuple[int, int]:
    """Return (n_correct, n_total)."""
    correct = sum(
        1 for c in citations if citation_is_correct(c, retrieved_hashes, retrieved_sources)
    )
    return correct, len(citations)


def is_refusal(text: str) -> bool:
    """Heuristic refusal detection (Vietnamese patterns)."""
    norm = normalize_text(text)
    return any(p in norm for p in REFUSAL_PATTERNS)


def answer_contains_rate(answer: str, phrases: list[str]) -> float | None:
    """Fraction of expected key phrases present in the answer (normalized).

    Empty phrase list → None (n/a, e.g. refusal-expected cases).
    """
    if not phrases:
        return None
    norm = normalize_text(answer)
    hits = sum(1 for p in phrases if normalize_text(p) and normalize_text(p) in norm)
    return hits / len(phrases)


def mean_or_none(values: list[float | None]) -> float | None:
    """Mean over non-None values; None when every value is None/empty."""
    valid = [v for v in values if isinstance(v, (int, float))]
    if not valid:
        return None
    return statistics.mean(valid)
