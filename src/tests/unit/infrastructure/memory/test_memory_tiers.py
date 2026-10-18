"""Unit tests for MemoryManager tiers (episodic)."""

from unittest.mock import MagicMock

from infrastructure.memory.memory_manager import MemoryConfig, MemoryManager


def _make_manager(episodic=None):
    mm = MemoryManager(config=MemoryConfig(auto_cleanup_enabled=False, episodic_enabled=False))
    mm.episodic = episodic
    return mm


def test_search_episodic_unavailable():
    mm = _make_manager(episodic=None)
    result = mm.search_memory("HPG?", memory_tiers=["episodic"], user_id="u1")
    assert result["episodic"]["count"] == 0
    assert result["episodic"]["error"] == "unavailable"


def test_search_episodic_tier():
    fake = MagicMock()
    fake.search_episodes.return_value = {"hits": [{"id": "1"}], "context": "ctx", "count": 1}
    mm = _make_manager(episodic=fake)
    result = mm.search_memory("HPG?", memory_tiers=["episodic"], user_id="u1")
    assert result["episodic"]["count"] == 1
    fake.search_episodes.assert_called_once_with(query="HPG?", user_id="u1", top_k=5)


def test_search_default_tiers_returns_nothing():
    """No tier requested -> nothing queried (short-term tiers no longer exist)."""
    mm = _make_manager(episodic=MagicMock())
    assert mm.search_memory("q", user_id="u1") == {}


def test_build_reformulation_inputs_shape():
    fake = MagicMock()
    fake.search_episodes.return_value = {"hits": [], "context": "", "count": 0}
    mm = _make_manager(episodic=fake)
    out = mm.build_reformulation_inputs("Ai là tác giả?", user_id="u1")
    assert set(out) == {"working", "sliding", "episodic"}
    assert out["working"]["current_raw_query"] == "Ai là tác giả?"
    assert out["sliding"]["count"] == 0
    assert out["episodic"]["count"] == 0


def test_clear_all_covers_episodic():
    fake = MagicMock()
    mm = _make_manager(episodic=fake)
    assert mm.clear_all(user_id="u1") is True
    fake.clear_user_episodes.assert_called_once_with("u1")


def test_get_stats_includes_episodic():
    fake = MagicMock()
    fake.count.return_value = 7
    mm = _make_manager(episodic=fake)
    stats = mm.get_stats(user_id="u1")
    assert stats["tiers"]["episodic"] == {"count": 7}
    assert stats["config"]["episodic_top_k"] == 5
