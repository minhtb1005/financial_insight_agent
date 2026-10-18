"""Embedder — NVIDIA key-pool only (rotating keys, dim 2048)."""

from __future__ import annotations

import os
from typing import Any

from infrastructure.observability import get_logger

# Ensure .env is loaded for API keys when run via cli without shell export
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

logger = get_logger("rag.embedder")

NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
NVIDIA_EMBEDDING_MODEL = os.getenv("NVIDIA_EMBEDDING_MODEL", "nvidia/nemotron-3-embed-1b")


class Embedder:
    def __init__(self, model: str | None = None, dim: int | None = None):
        self.model = model or NVIDIA_EMBEDDING_MODEL
        self.dim = dim or 2048
        self._nvidia_client: Any = None
        self._pool: Any = None
        self._init_clients()

    def _init_clients(self) -> None:
        from infrastructure.llm.nvidia_key_pool import NvidiaKeyPool

        self._pool = NvidiaKeyPool()
        if len(self._pool):
            try:
                from openai import OpenAI

                self._nvidia_client = OpenAI(base_url=NVIDIA_BASE_URL, api_key=self._pool.keys[0])
            except Exception as e:
                logger.warning("NVIDIA embed init failed: %s", e)

    @property
    def provider(self) -> str:
        if self._nvidia_client:
            return "nvidia"
        return "none"

    def _create(self, client, batch: list[str], input_type: str | None) -> list[list[float]]:
        """Create embeddings, trying input_type via extra_body, retrying plain on 400."""
        if input_type:
            try:
                resp = client.embeddings.create(
                    model=self.model, input=batch, extra_body={"input_type": input_type}
                )
                return [d.embedding for d in resp.data]
            except Exception as e:
                if "400" not in str(e) and "status_code" not in type(e).__name__.lower():
                    # Only swallow 400-style rejections; re-raise auth/rate-limit.
                    etype = type(e).__name__
                    if etype in (
                        "AuthenticationError",
                        "RateLimitError",
                        "InternalServerError",
                        "ServiceUnavailableError",
                        "APITimeoutError",
                        "APIConnectionError",
                    ):
                        raise
                logger.info("input_type rejected, retrying plain: %s", e)
        resp = client.embeddings.create(model=self.model, input=batch)
        return [d.embedding for d in resp.data]

    def embed(self, texts: list[str], input_type: str = "passage") -> list[list[float]]:
        if not texts:
            return []
        if not (self._nvidia_client and self._pool and len(self._pool)):
            raise RuntimeError(
                "No NVIDIA embedding key — set NVIDIA_API_KEY* (embedding is NVIDIA-only)"
            )
        # batch size 100 to avoid token limit
        out: list[list[float]] = []
        for i in range(0, len(texts), 100):
            batch = texts[i : i + 100]
            done = False
            for _ in range(len(self._pool)):
                key = self._pool.get_next()
                if key is None:
                    break
                self._nvidia_client.api_key = key
                try:
                    out.extend(self._create(self._nvidia_client, batch, input_type))
                    self._pool.report_success(key)
                    done = True
                    break
                except Exception as e:
                    etype = type(e).__name__
                    if etype in (
                        "AuthenticationError",
                        "RateLimitError",
                        "InternalServerError",
                        "ServiceUnavailableError",
                        "APITimeoutError",
                        "APIConnectionError",
                    ):
                        status = getattr(e, "status_code", None)
                        self._pool.report_failure(key, status if isinstance(status, int) else None)
                        continue
                    raise
            if not done:
                raise RuntimeError("All NVIDIA keys failed for embed batch")
        if out:
            self.dim = len(out[0])
        return out


def embed_query(query: str, embedder: Embedder | None = None) -> list[float]:
    emb = embedder or Embedder()
    return emb.embed([query], input_type="query")[0]
