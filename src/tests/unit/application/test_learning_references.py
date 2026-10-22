"""Reviewed content survives stale indexes and absent network providers."""

from unittest.mock import patch

from application.learning.policy import LearningContext
from infrastructure.rag import retriever


def test_general_tax_question_gets_current_period_without_lesson_id():
    prompt = LearningContext().prompt("Tôi cần tính thuế lương nhưng chưa biết mức lương")
    assert "15.500.000" in prompt and "6.200.000" in prompt
    assert "kỳ tính thuế 2026" in prompt
    assert "thiếu lương/cư trú/kỳ/giảm trừ thì hỏi" in prompt


def test_stale_vector_seed_is_replaced_in_both_hits_and_context():
    stale = {
        "score": 0.9,
        "payload": {
            "source_id": "tt_135_2025",
            "text": "Điều 12: chatbot bất hợp pháp",
            "priority": 2,
        },
    }
    with (
        patch.object(retriever, "embed_query", return_value=[0.0]),
        patch.object(retriever, "vs_search", return_value=[stale]),
    ):
        result = retriever.search_knowledge("chứng chỉ", top_k=1)
    assert "chatbot bất hợp pháp" not in str(result)
    assert result["hits"][0]["payload"]["kind"] == "editorial_summary"
    assert result["hits"][0]["score"] is None
    assert "Điều8/Điều12" in result["context"]


def test_reviewed_insurance_is_available_when_embeddings_fail():
    with patch.object(retriever, "embed_query", side_effect=ConnectionError("offline")):
        result = retriever.search_knowledge("Thời gian cân nhắc bảo hiểm", top_k=1)
    assert "21 ngày" in result["context"]
    assert result["count"] == 1
    assert result["retrieval_error"] == "offline"
    assert result["hits"][0]["payload"]["reviewed_at"] == "2026-10-22"


def test_unrelated_outage_stays_visible_instead_of_returning_fake_evidence():
    with patch.object(retriever, "embed_query", side_effect=ConnectionError("offline")):
        result = retriever.search_knowledge("unknown xyz")
    assert result["hits"] == [] and result["error"] == "offline"


def test_unsafe_seed_articles_are_not_reintroduced_by_ingestion():
    from infrastructure.rag.ingestion.connectors import SEED_TEXTS

    assert "4. Cổ phiếu" not in SEED_TEXTS["vbpl_24_2025"]
    assert "Điều 12. Tư vấn đầu tư" not in SEED_TEXTS["tt_135_2025"]
    assert "thay TT11/2021" in SEED_TEXTS["cic_debt_groups"]


def test_forecast_question_cannot_skip_explanation_after_a_chart():
    from application.agents.agent import _needs_chart_explanation

    assert _needs_chart_explanation("Vẽ VNM 6 tháng rồi dự báo ngày mai chắc chắn tăng bao nhiêu.")
