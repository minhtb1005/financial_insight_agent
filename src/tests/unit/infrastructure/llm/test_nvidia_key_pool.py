"""Unit tests for NvidiaKeyPool + NVIDIARotatingChat (mocked, no network)."""

import threading
from unittest.mock import MagicMock, patch

import pytest


def _pool3():
    from infrastructure.llm.nvidia_key_pool import NvidiaKeyPool

    return NvidiaKeyPool(keys=["k1", "k2", "k3"], cooldown_s=60)


def test_round_robin_cycles():
    pool = _pool3()
    assert [pool.get_next() for _ in range(4)] == ["k1", "k2", "k3", "k1"]


def test_cooldown_skip_and_recovery():
    pool = _pool3()
    pool.report_failure("k1", 429)
    got = {pool.get_next() for _ in range(4)}
    assert "k1" not in got
    pool.report_success("k1")
    assert "k1" in {pool.get_next() for _ in range(6)}


def test_all_cooling_returns_none():
    pool = _pool3()
    for k in ("k1", "k2", "k3"):
        pool.report_failure(k, 503)
    assert pool.get_next() is None


def test_non_rotate_status_keeps_key_usable():
    pool = _pool3()
    pool.report_failure("k1", 400)  # not in rotate set → no cooldown
    assert "k1" in {pool.get_next() for _ in range(6)}


def test_thread_safety_smoke():
    pool = _pool3()
    seen = []
    lock = threading.Lock()

    def worker():
        for _ in range(200):
            k = pool.get_next()
            with lock:
                seen.append(k)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(seen) == 1600 and all(k in ("k1", "k2", "k3") for k in seen)


def test_rotating_chat_retries_next_key_per_invoke():
    from infrastructure.llm.llm_provider import NVIDIARotatingChat

    pool = _pool3()
    err = type("RateLimitError", (Exception,), {})("boom")  # classified retryable by LLMChain

    good = MagicMock()
    good.invoke.return_value = MagicMock(content="ok")
    built = {"n": 0}

    def fake_build(key):
        built["n"] += 1
        m = MagicMock()
        if built["n"] == 1:
            m.invoke.side_effect = err
            return m
        return good

    chat = NVIDIARotatingChat(pool, model="nvidia/x")
    chat._build = fake_build  # type: ignore
    assert chat.invoke("hi").content == "ok"
    assert built["n"] == 2


def test_rotating_chat_wrappers_keep_rotating():
    from infrastructure.llm.llm_provider import NVIDIARotatingChat

    pool = _pool3()
    chat = NVIDIARotatingChat(pool)
    s = chat.with_structured_output(MagicMock)
    assert isinstance(s, NVIDIARotatingChat) and s._pool is pool and s._schema is not None
    t = chat.bind_tools([])
    assert isinstance(t, NVIDIARotatingChat) and t._pool is pool and t._tools == []


def test_rotating_chat_no_keys_raises():
    from infrastructure.llm.llm_provider import NVIDIARotatingChat
    from infrastructure.llm.nvidia_key_pool import NvidiaKeyPool
    from infrastructure.resilience.circuit_breaker import LLMUnavailableError

    chat = NVIDIARotatingChat(NvidiaKeyPool(keys=[]))
    with pytest.raises(LLMUnavailableError):
        chat.invoke("hi")


@patch("openai.OpenAI")
def test_embedder_nvidia_primary_mocked(mock_openai):
    from infrastructure.rag.embedder import Embedder

    inst = MagicMock()
    inst.embeddings.create.return_value.data = [MagicMock(embedding=[0.1] * 2048)]
    mock_openai.return_value = inst

    with patch.dict("os.environ", {"NVIDIA_API_KEY": "nv-test", "NVIDIA_API_KEY2": "", "NVIDIA_API_KEY3": ""}):
        emb = Embedder()
    assert emb.provider == "nvidia"
    assert emb.embed(["hello"]) == [[0.1] * 2048]
    assert emb.dim == 2048
