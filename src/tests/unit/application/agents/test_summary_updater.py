"""Unit tests for SummaryUpdater (never calls LLM, nothing persisted)."""

from application.agents.summary_updater import SummaryUpdater


def test_update_passes_llm_entities():
    updater = SummaryUpdater()
    out = updater.update(
        user_id="u1",
        entities=["HPG"],
        topics=["steel"],
        raw_query="Giá của nó?",
        rewritten_query="Giá HPG?",
    )
    assert out["entities"] == ["HPG"]
    assert out["topics"] == ["steel"]
    assert out["updated_at"] is None


def test_fallback_extracts_known_tickers():
    updater = SummaryUpdater()
    out = updater.update(
        user_id="u1",
        entities=[],
        topics=[],
        raw_query="còn VIC thì sao?",
        rewritten_query="Giá VIC bao nhiêu?",
    )
    assert "VIC" in out["entities"]


def test_fallback_ignores_unknown_tokens():
    updater = SummaryUpdater()
    out = updater.update(
        user_id="u1",
        entities=[],
        topics=[],
        raw_query="Ai là tác giả của nó?",
        rewritten_query="Ai là tác giả?",
    )
    assert out["entities"] == []


def test_extract_tickers_prefers_rewritten():
    from infrastructure.guardrails.tickers import VIETNAMESE_TICKERS

    found = SummaryUpdater._extract_tickers(
        "còn nó thì sao?", "Giá HPG và VCB?", VIETNAMESE_TICKERS
    )
    assert found == ["HPG", "VCB"]
