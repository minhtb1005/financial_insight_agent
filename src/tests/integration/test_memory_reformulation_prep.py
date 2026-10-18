"""Integration: episodic memory against real Qdrant.

Skips cleanly when infra is unavailable. Qdrant uses an isolated embedded dir
under tmp_path (no docker needed).
"""

import time
import uuid

import pytest

pytestmark = pytest.mark.integration


@pytest.fixture
def user_id():
    return f"itest-{uuid.uuid4().hex[:8]}"


def test_episodic_against_embedded_qdrant(user_id, tmp_path, monkeypatch):
    from infrastructure.memory.episodic.store import EpisodicStore
    from infrastructure.rag.embedder import Embedder

    try:
        embedder = Embedder()
    except Exception as e:
        pytest.skip(f"no embedding provider: {e}")
    if embedder.provider == "none":
        pytest.skip("no embedding provider available")

    monkeypatch.setenv("QDRANT_PATH", str(tmp_path / "qdrant"))
    monkeypatch.setenv("QDRANT_FORCE_LOCAL", "true")
    store = EpisodicStore(
        collection=f"itest_episodic_{uuid.uuid4().hex[:8]}",
        embedder=embedder,
        min_score=0.0,
    )
    texts = [
        "HPG là cổ phiếu ngành thép trên HOSE",
        "VCB là ngân hàng Vietcombank",
        "FPT là tập đoàn công nghệ thông tin",
    ]
    for t in texts:
        assert store.add_episode(user_id=user_id, text=t) is not None

    # wait briefly for embedded index visibility (usually immediate)
    deadline = time.time() + 10
    result = {"count": 0}
    while time.time() < deadline:
        result = store.search_episodes("cổ phiếu thép HPG", user_id=user_id, top_k=3)
        if result["count"] >= 1:
            break
        time.sleep(0.5)
    assert result["count"] >= 1
    assert all(h["payload"]["user_id"] == user_id for h in result["hits"])
    assert "thép" in result["context"] or "HPG" in result["context"]

    other = store.search_episodes("cổ phiếu thép HPG", user_id="ghost-user", top_k=3)
    assert other["count"] == 0

    assert store.count(user_id) == 3
    assert store.clear_user_episodes(user_id) == 3
    assert store.count(user_id) == 0
