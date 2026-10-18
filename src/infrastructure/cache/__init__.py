"""
Cache infrastructure package for the financial insight agent.

Provides the in-memory (L1) cache used as the CachePort backing store.
"""

from __future__ import annotations

__all__ = [
    "MemoryCache",
    "get_memory_cache",
    "make_cache_key",
    "make_overview_cache_key",
]


def __getattr__(name):
    import importlib

    _LAZY = {
        "MemoryCache": ".memory_cache",
        "get_memory_cache": ".memory_cache",
        "make_cache_key": ".cache_keys",
        "make_overview_cache_key": ".cache_keys",
    }
    if name in _LAZY:
        mod = importlib.import_module(_LAZY[name], __package__)
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
