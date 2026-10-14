"""Round-robin NVIDIA API key pool with cooldown (shared by chat + embed)."""

from __future__ import annotations

import os
import threading
import time

from infrastructure.observability import get_logger

logger = get_logger("llm.nvidia_pool")

# HTTP statuses that mean "try the next key in this same request".
_ROTATE_STATUSES = frozenset({401, 403, 429, 500, 502, 503, 504})


def _load_keys() -> list[str]:
    keys = [os.getenv("NVIDIA_API_KEY"), os.getenv("NVIDIA_API_KEY2"), os.getenv("NVIDIA_API_KEY3")]
    return [k.strip() for k in keys if k and k.strip()]


def _cooldown_seconds() -> float:
    try:
        return float(os.getenv("NVIDIA_KEY_COOLDOWN_S", "60"))
    except (ValueError, TypeError):
        return 60.0


class NvidiaKeyPool:
    """Thread-safe round-robin over NVIDIA keys, skipping cooled-down keys.

    Short `threading.Lock` critical sections only (no await inside), so it is
    safe for both sync and async callers.
    """

    def __init__(self, keys: list[str] | None = None, cooldown_s: float | None = None):
        self._keys = keys if keys is not None else _load_keys()
        self._cooldown_s = cooldown_s if cooldown_s is not None else _cooldown_seconds()
        self._lock = threading.Lock()
        self._idx = 0
        self._cooldown_until: dict[str, float] = {}
        self.fail_count = 0
        self.throttled_count = 0

    @property
    def keys(self) -> list[str]:
        return list(self._keys)

    def __len__(self) -> int:
        return len(self._keys)

    def get_next(self) -> str | None:
        """Next usable key (round-robin, skipping keys in cooldown)."""
        with self._lock:
            if not self._keys:
                return None
            now = time.time()
            for _ in range(len(self._keys)):
                key = self._keys[self._idx % len(self._keys)]
                self._idx += 1
                if self._cooldown_until.get(key, 0) <= now:
                    return key
            return None  # all cooling down

    def report_success(self, key: str) -> None:
        with self._lock:
            self._cooldown_until.pop(key, None)

    def report_failure(self, key: str, status: int | None = None) -> None:
        """Cooldown the key when status is None (unknown error) or rotate-worthy."""
        with self._lock:
            self.fail_count += 1
            if status == 429:
                self.throttled_count += 1
            if status is None or status in _ROTATE_STATUSES:
                self._cooldown_until[key] = time.time() + self._cooldown_s
                logger.warning("NVIDIA key ...%s cooling down (status=%s)", key[-4:], status)


_pool: NvidiaKeyPool | None = None
_pool_lock = threading.Lock()


def get_pool() -> NvidiaKeyPool:
    """Process-wide shared pool (chat + embed use the same one)."""
    global _pool
    with _pool_lock:
        if _pool is None:
            _pool = NvidiaKeyPool()
        return _pool
