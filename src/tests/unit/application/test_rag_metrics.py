"""Unit tests for evals/rag_metrics.py (pure functions, no DB/LLM)."""

import sys
from pathlib import Path

EVALS_DIR = Path(__file__).parents[4] / "evals"
sys.path.insert(0, str(EVALS_DIR))

import pytest  # noqa: E402

from rag_metrics import (  # noqa: E402
    answer_contains_rate,
    citation_correctness,
    citation_is_correct,
    extract_citations,
    hit_rate_at_k,
    is_refusal,
    mean_or_none,
    normalize_text,
    precision_at_k,
    recall_at_k,
)


class TestNormalize:
    def test_collapse_whitespace_and_case(self):
        assert normalize_text("  Chào   BẠN\n") == "chào bạn"


class TestRetrievalScores:
    def test_precision_basic(self):
        assert precision_at_k(["a", "b", "c"], {"a", "c"}, 3) == pytest.approx(2 / 3)

    def test_precision_empty_retrieval(self):
        assert precision_at_k([], {"a"}, 5) == 0.0

    def test_precision_k_larger_than_returned(self):
        # only 1 hit returned, k=5 -> 1/5
        assert precision_at_k(["a"], {"a", "b"}, 5) == pytest.approx(0.2)

    def test_precision_bad_k(self):
        with pytest.raises(ValueError):
            precision_at_k(["a"], {"a"}, 0)

    def test_recall_basic(self):
        assert recall_at_k(["a", "x"], {"a", "b"}, 5) == pytest.approx(0.5)

    def test_recall_empty_expected_is_none(self):
        assert recall_at_k(["a"], set(), 5) is None

    def test_recall_empty_retrieval(self):
        assert recall_at_k([], {"a"}, 5) == 0.0

    def test_hit_rate(self):
        assert hit_rate_at_k(["x", "a"], {"a"}, 5) == 1.0
        assert hit_rate_at_k(["x", "y"], {"a"}, 5) == 0.0
        assert hit_rate_at_k([], set(), 5) is None


class TestCitations:
    def test_extract(self):
        text = "Theo luật [vbpl_24_2025:bca88e90] và [tt_96_2020]."
        assert extract_citations(text) == ["vbpl_24_2025:bca88e90", "tt_96_2020"]

    def test_extract_none(self):
        assert extract_citations("không có trích dẫn") == []

    def test_full_hash_correct(self):
        assert citation_is_correct("src:deadbeefcafe0001", ["deadbeefcafe0001"], ["src"])

    def test_prefix_correct(self):
        assert citation_is_correct("src:deadbeef", ["deadbeefcafe0001"], ["src"])

    def test_short_prefix_rejected(self):
        assert not citation_is_correct("src:dead", ["deadbeefcafe0001"], ["src"])

    def test_bare_source_correct(self):
        assert citation_is_correct("src", ["deadbeefcafe0001"], ["src", "other"])

    def test_hallucinated_source_rejected(self):
        assert not citation_is_correct("fake:deadbeef", ["deadbeefcafe0001"], ["src"])

    def test_hallucinated_hash_rejected(self):
        assert not citation_is_correct("src:00000000", ["deadbeefcafe0001"], ["src"])

    def test_counts(self):
        ok, tot = citation_correctness(
            ["src:deadbeef", "fake:00000000"], ["deadbeefcafe0001"], ["src"])
        assert (ok, tot) == (1, 2)


class TestRefusal:
    def test_refusal_sentence(self):
        from rag_metrics import REFUSAL_SENTENCE

        assert is_refusal(REFUSAL_SENTENCE)

    def test_paraphrase_refusal(self):
        assert is_refusal("Xin lỗi, câu hỏi này nằm ngoài phạm vi cơ sở tri thức.")

    def test_answer_not_refusal(self):
        assert not is_refusal("Theo [vbpl_24_2025:bca88e90], cổ phiếu là chứng khoán.")


class TestAnswerContains:
    def test_rate(self):
        assert answer_contains_rate("Cổ phiếu  xác nhận quyền", ["cổ phiếu", "trái phiếu"]) == pytest.approx(0.5)

    def test_empty_phrases_none(self):
        assert answer_contains_rate("bất kỳ", []) is None


class TestMean:
    def test_skips_none(self):
        assert mean_or_none([1.0, None, 0.0]) == pytest.approx(0.5)

    def test_all_none(self):
        assert mean_or_none([None, None]) is None
        assert mean_or_none([]) is None
