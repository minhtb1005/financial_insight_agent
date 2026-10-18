"""Unit tests for MemoryManager (all external deps mocked)."""

from unittest.mock import patch

from infrastructure.memory.memory_manager import MemoryConfig, MemoryManager


def _make_manager(config=None):
    if config is None:
        config = MemoryConfig(auto_cleanup_enabled=False)
    return MemoryManager(config=config)


# -- Constructor ----------------------------------------------------------


def test_init_with_defaults():
    mm = MemoryManager()
    assert mm.config is not None
    assert mm.config.auto_cleanup_enabled is True


def test_init_with_custom_config():
    cfg = MemoryConfig(auto_cleanup_enabled=False)
    mm = _make_manager(config=cfg)
    assert mm.config.auto_cleanup_enabled is False


# -- add_interaction / search_memory (short-term tier removed) ------------


def test_add_interaction_is_noop():
    """No short-term store any more -> always reports "not stored"."""
    mm = _make_manager()
    assert mm.add_interaction(user_query="what is VCB", agent_response="a bank") is False


def test_add_interaction_none_response():
    mm = _make_manager()
    assert mm.add_interaction(user_query="key2", agent_response=None) is False


def test_search_memory_returns_empty_without_tiers():
    mm = _make_manager()
    assert mm.search_memory("VCB") == {}


# -- background tasks -----------------------------------------------------


def test_start_background_tasks():
    mm = _make_manager()
    with patch("threading.Thread") as mock_thread:
        mm.start_background_tasks()
    assert mock_thread.called
    assert mock_thread.call_args[1].get("daemon") is True


def test_stop_background_tasks():
    mm = _make_manager()
    mm.stop_background_tasks()
    assert mm._stop_event.is_set()
