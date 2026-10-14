"""Embedder — NVIDIA primary, OpenAI legacy + sentence-transformers fallback."""

from __future__ import annotations

import os

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
        self.dim = dim or (2048 if self.model.startswith("nvidia/") else 1536)
        self._nvidia_client = None
        self._openai_client = None
        self._st_model = None
        self._pool = None
        self._init_clients()

    def _init_clients(self) -> None:
        from infrastructure.llm.nvidia_key_pool import NvidiaKeyPool

        self._pool = NvidiaKeyPool()
        if len(self._pool):
            try:
                from openai import OpenAI

                self._nvidia_client = OpenAI(
                    base_url=NVIDIA_BASE_URL, api_key=self._pool.keys[0]
                )
            except Exception as e:
                logger.warning("NVIDIA embed init failed: %s", e)
        key = os.getenv("OPENAI_API_KEY")
        if key:
            try:
                from openai import OpenAI

                self._openai_client = OpenAI(api_key=key)
            except Exception as e:
                logger.warning("OpenAI embed init failed: %s", e)
        if not self._nvidia_client and not self._openai_client:
            # fallback local
            try:
                from sentence_transformers import SentenceTransformer

                # multilingual for Vietnamese
                self._st_model = SentenceTransformer("intfloat/multilingual-e5-base")
                self.dim = 768
                logger.info("Using sentence-transformers fallback, dim=768")
            except Exception as e:
                logger.warning("sentence-transformers init failed: %s", e)

    @property
    def provider(self) -> str:
        if self._nvidia_client:
            return "nvidia"
        if self._openai_client:
            return "openai"
        if self._st_model:
            return "sentence_transformers"
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
                    if etype in ("AuthenticationError", "RateLimitError",
                                 "InternalServerError", "ServiceUnavailableError",
                                 "APITimeoutError", "APIConnectionError"):
                        raise
                logger.info("input_type rejected, retrying plain: %s", e)
        resp = client.embeddings.create(model=self.model, input=batch)
        return [d.embedding for d in resp.data]

    def embed(self, texts: list[str], input_type: str = "passage") -> list[list[float]]:
        if not texts:
            return []
        if self._nvidia_client and self._pool and len(self._pool):
            try:
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
                            if etype in ("AuthenticationError", "RateLimitError",
                                         "InternalServerError", "ServiceUnavailableError",
                                         "APITimeoutError", "APIConnectionError"):
                                status = getattr(e, "status_code", None)
                                self._pool.report_failure(key, status if isinstance(status, int) else None)
                                continue
                            raise
                    if not done:
                        raise RuntimeError("All NVIDIA keys failed for embed batch")
                if out:
                    self.dim = len(out[0])
                return out
            except Exception as e:
                logger.warning("NVIDIA embed failed, trying fallback: %s", e)
        if self._openai_client:
            try:
                legacy_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
                out = []
                for i in range(0, len(texts), 100):
                    batch = texts[i : i + 100]
                    resp = self._openai_client.embeddings.create(model=legacy_model, input=batch)
                    for d in resp.data:
                        out.append(d.embedding)
                if out:
                    self.dim = len(out[0])
                return out
            except Exception as e:
                logger.warning("OpenAI embed failed, trying fallback: %s", e)
                if self._st_model:
                    return self._st_model.encode(texts, normalize_embeddings=True).tolist()  # type: ignore
                raise
        if self._st_model:
            return self._st_model.encode(texts, normalize_embeddings=True).tolist()  # type: ignore
        raise RuntimeError("No embedding provider available — set NVIDIA_API_KEY or OPENAI_API_KEY or install sentence-transformers")


def embed_query(query: str, embedder: Embedder | None = None) -> list[float]:
    emb = embedder or Embedder()
    return emb.embed([query], input_type="query")[0]
