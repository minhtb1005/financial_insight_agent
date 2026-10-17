import os
import time
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq

from infrastructure.observability import get_logger
from infrastructure.observability.logging.logger import request_id_var
from infrastructure.observability.tracing import SpanKind, get_tracer
from infrastructure.resilience.circuit_breaker import LLMUnavailableError, create_circuit_breaker

_RETRYABLE_ERRORS = frozenset(
    {
        "RateLimitError",
        "InternalServerError",
        "ServiceUnavailableError",
        "APITimeoutError",
        "APIConnectionError",
    }
)

_AUTH_ERRORS = frozenset(
    {
        "AuthenticationError",
        "PermissionDeniedError",
        "ForbiddenError",
    }
)

logger = get_logger("llm_provider")

NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
NVIDIA_CHAT_MODEL = os.getenv("NVIDIA_CHAT_MODEL", "nvidia/nemotron-3-ultra-550b-a55b")

_OPENAI_KNOWN_KWARGS = {
    "temperature",
    "max_tokens",
    "top_p",
    "frequency_penalty",
    "presence_penalty",
    "stop",
    "n",
    "stream",
    "model",
    "response_format",
    "seed",
    "tools",
    "tool_choice",
}

_GROQ_KNOWN_KWARGS = {
    "temperature",
    "max_tokens",
    "top_p",
    "stop",
    "stream",
    "model",
}


class MultiQuery(BaseModel):
    queries: list[str]


class ReformulatedQuery(BaseModel):
    """Self-contained rewrite of a context-dependent follow-up question."""

    rewritten: str
    entities: list[str] = []
    topics: list[str] = []


class NVIDIARotatingChat:
    """ChatOpenAI-compatible wrapper rotating NVIDIA keys per invoke.

    Key is picked at invoke-time (never at bind-time), so
    `with_structured_output` / `bind_tools` derivatives keep rotating.
    Each attempt builds a fresh ChatOpenAI with max_retries=0 so the SDK
    never masks pool rotation by retrying a dead key.
    """

    def __init__(
        self,
        pool,
        model: str | None = None,
        base_url: str | None = None,
        schema=None,
        method: str = "json_mode",
        tools=None,
    ):
        from infrastructure.llm.nvidia_key_pool import get_pool

        self._pool = pool if pool is not None else get_pool()
        self._model = model or NVIDIA_CHAT_MODEL
        self._base_url = base_url or NVIDIA_BASE_URL
        self._schema = schema
        self._method = method
        self._tools = tools

    @property
    def model(self) -> str:
        return self._model

    def with_structured_output(self, pydantic_object, method: str = "json_mode"):
        return NVIDIARotatingChat(
            self._pool,
            self._model,
            self._base_url,
            schema=pydantic_object,
            method=method,
            tools=self._tools,
        )

    def bind_tools(self, tools, **kwargs):  # noqa: ARG002
        return NVIDIARotatingChat(
            self._pool,
            self._model,
            self._base_url,
            schema=self._schema,
            method=self._method,
            tools=tools,
        )

    def _build(self, api_key: str):
        llm = ChatOpenAI(
            base_url=self._base_url,
            api_key=api_key,
            model=self._model,
            temperature=0,
            max_tokens=4096,
            max_retries=0,
        )
        if self._schema is not None:
            llm = llm.with_structured_output(self._schema, method=self._method)
        if self._tools is not None:
            llm = llm.bind_tools(self._tools)
        return llm

    @staticmethod
    def _status_of(error: Exception) -> int | None:
        for attr in ("status_code", "status"):
            v = getattr(error, attr, None)
            if isinstance(v, int):
                return v
        resp = getattr(error, "response", None)
        v = getattr(resp, "status_code", None)
        return v if isinstance(v, int) else None

    def invoke(self, messages, **kwargs):
        keys = self._pool.keys
        if not keys:
            raise LLMUnavailableError("No NVIDIA API keys configured")
        last_error: Exception | None = None
        for _ in range(len(keys)):
            key = self._pool.get_next()
            if key is None:
                break
            try:
                result = self._build(key).invoke(messages, **kwargs)
                self._pool.report_success(key)
                return result
            except Exception as e:
                category = LLMChain._classify_error(e)
                if category in ("retryable", "auth"):
                    self._pool.report_failure(key, self._status_of(e))
                    last_error = e
                    continue
                raise
        if last_error is not None:
            raise last_error
        raise LLMUnavailableError("All NVIDIA keys cooling down")


class LLMChain:
    def __init__(self, primary, fallback, openai_cb, groq_cb, label: str):
        self._primary = primary
        self._fallback = fallback
        self._openai_cb = openai_cb
        self._groq_cb = groq_cb
        self._label = label
        self._openai_kwarg_keys = _OPENAI_KNOWN_KWARGS
        self._groq_kwarg_keys = _GROQ_KNOWN_KWARGS

    @staticmethod
    def _filter_kwargs(kwargs, allowed_keys):
        return {k: v for k, v in kwargs.items() if k in allowed_keys}

    @staticmethod
    def _classify_error(error: Exception) -> str:
        error_type = type(error).__name__
        if error_type in _RETRYABLE_ERRORS:
            return "retryable"
        if error_type in _AUTH_ERRORS:
            return "auth"
        return "unknown"

    def _try_provider(
        self, provider_name: str, llm, cb, messages, kwargs, rid: str
    ):  # noqa: PLR0917
        """Try a single provider. Returns (result, error) tuple."""
        try:
            start = time.time()
            result = llm.invoke(messages, **kwargs)
            cb.record_success()
            logger.info(
                "%s %s LLM call succeeded",
                provider_name.title(),
                self._label,
                extra={
                    "request_id": rid,
                    "provider": provider_name,
                    "duration_ms": round((time.time() - start) * 1000, 2),
                },
            )
            return result, None
        except Exception as e:
            error_type = type(e).__name__
            category = self._classify_error(e)

            log_extra = {
                "request_id": rid,
                "provider": provider_name,
                "error_type": error_type,
                "error_category": category,
                "error": str(e),
            }

            if category == "retryable":
                logger.warning("%s retryable error", provider_name.title(), extra=log_extra)
            elif category == "auth":
                logger.error("%s auth error", provider_name.title(), extra=log_extra)
                cb.record_failure()
            else:
                logger.warning("%s LLM failed", provider_name.title(), extra=log_extra)
                cb.record_failure()

            return None, e

    def invoke(self, messages, **kwargs):
        rid = request_id_var.get() or "unknown"
        last_error = None

        tracer = get_tracer()
        with tracer.start_span(
            "llm_provider.chain",
            SpanKind.LLM,
            attributes={"request_id": rid, "label": self._label},
            inputs={"message_count": len(messages)},
        ) as span:
            openai_kwargs = self._filter_kwargs(kwargs, self._openai_kwarg_keys)
            groq_kwargs = self._filter_kwargs(kwargs, self._groq_kwarg_keys)

            if self._primary and self._openai_cb.acquire_permit():
                result, err = self._try_provider(
                    "openai", self._primary, self._openai_cb, messages, openai_kwargs, rid
                )
                if err is None:
                    if span is not None:
                        span.provider = "openai"
                        span.model = getattr(self._primary, "model_name", None) or getattr(
                            self._primary, "model", None
                        )
                        span.attributes["fallback_used"] = False
                    return result
                last_error = err
                if span is not None:
                    span.attributes["openai_error"] = f"{type(err).__name__}: {err}"

            if self._fallback and self._groq_cb.acquire_permit():
                result, err = self._try_provider(
                    "groq", self._fallback, self._groq_cb, messages, groq_kwargs, rid
                )
                if err is None:
                    if span is not None:
                        span.provider = "groq"
                        span.model = getattr(self._fallback, "model_name", None)
                        span.attributes["fallback_used"] = True
                    return result
                last_error = err

            if span is not None and last_error is not None:
                span.attributes["all_providers_failed"] = True

        if last_error:
            raise last_error
        raise LLMUnavailableError(
            "No LLM providers available: both NVIDIA and Groq are unreachable"
        )


class LLMProvider:
    def __init__(self):
        load_dotenv()
        self._chain_cache: dict[str, LLMChain] = {}

        openai_api_key = os.getenv("OPENAI_API_KEY")
        groq_api_key = os.getenv("GROQ_API_KEY")

        from infrastructure.llm.nvidia_key_pool import NvidiaKeyPool

        self._pool = NvidiaKeyPool()
        if len(self._pool):
            self._primary = NVIDIARotatingChat(self._pool)
        elif openai_api_key:
            logger.warning("No NVIDIA keys — falling back to legacy OpenAI primary")
            self._primary = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0,
                api_key=openai_api_key,
                max_retries=3,
            )
        else:
            logger.warning("NVIDIA_API_KEY* not set — skipping primary LLM")
            self._primary = None

        if groq_api_key:
            self._fallback = ChatGroq(
                model="llama-3.1-8b-instant",
                temperature=0,
                api_key=groq_api_key,
                max_retries=3,
            )
        else:
            logger.warning("GROQ_API_KEY not set — fallback LLM (Groq) disabled")
            self._fallback = None

        self._openai_cb = create_circuit_breaker(name="llm_openai")
        self._groq_cb = create_circuit_breaker(name="llm_groq")

    def invoke_with_fallback(self, messages, model_kwargs: dict | None = None):
        """Invoke LLM with automatic primary → fallback chain.

        Delegates to LLMChain to avoid duplicating the retry logic.
        """
        model_kwargs = model_kwargs or {}

        if self._primary is None and self._fallback is None:
            raise LLMUnavailableError(
                "No LLM providers available: NVIDIA/OpenAI and GROQ keys are all missing"
            )

        chain = self._make_chain(self._primary, self._fallback, "invoke")
        return chain.invoke(messages, **model_kwargs)

    def _make_chain(self, primary, fallback, label) -> "LLMChain":
        cache_key = f"{label}:{id(primary)}:{id(fallback)}"
        cached = self._chain_cache.get(cache_key)
        if cached:
            return cached
        chain = LLMChain(
            primary=primary,
            fallback=fallback,
            openai_cb=self._openai_cb,
            groq_cb=self._groq_cb,
            label=label,
        )
        self._chain_cache[cache_key] = chain
        return chain

    def with_structured_output(
        self,
        pydantic_object,
        method: str = "json_mode",
        fallback: bool = False,
    ):
        if self._primary is None and self._fallback is None:
            raise LLMUnavailableError(
                "No LLM providers available: NVIDIA/OpenAI and GROQ keys are all missing"
            )

        primary = (
            self._primary.with_structured_output(pydantic_object, method=method)
            if self._primary
            else None
        )
        fallback_llm = (
            self._fallback.with_structured_output(pydantic_object, method=method)
            if self._fallback
            else None
        )

        if not fallback or primary is None:
            if fallback_llm:
                return fallback_llm
            if primary:
                return primary
            raise LLMUnavailableError(
                "No LLM providers available: NVIDIA/OpenAI and GROQ keys are all missing"
            )

        return self._make_chain(primary, fallback_llm, "structured")

    def get_tool_calling_llm(self, tools, **kwargs):  # noqa: ARG002 — API-compat passthrough
        if self._primary is None and self._fallback is None:
            raise LLMUnavailableError(
                "No LLM providers available: NVIDIA/OpenAI and GROQ keys are all missing"
            )

        primary = self._primary.bind_tools(tools) if self._primary else None
        fallback_llm = self._fallback.bind_tools(tools) if self._fallback else None

        if not fallback_llm and primary is None:
            raise LLMUnavailableError(
                "No LLM providers available: both NVIDIA and Groq are unreachable"
            )

        return self._make_chain(primary, fallback_llm, "tool-calling")
