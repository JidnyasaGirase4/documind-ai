"""Configurable LLM adapter. Providers: anthropic, openai (any OpenAI-compatible endpoint), ollama (local), mock.

Failures are translated into clean API errors: missing credentials (503), timeouts (503),
rate limits (429) and provider errors (503). The `mock` provider is DEVELOPMENT-ONLY: its
output is always prefixed so it can never be mistaken for a real AI answer."""

import re
from typing import Protocol

import httpx

from app.core.config import settings
from app.core.errors import AppError

MOCK_PREFIX = "[DEVELOPMENT MOCK - not a real AI answer]"


class LLMProvider(Protocol):
    def generate(self, system: str, messages: list[dict]) -> str: ...


def _not_configured(detail: str) -> AppError:
    return AppError(503, "LLM_NOT_CONFIGURED", f"The AI provider is not configured: {detail}")


def _http_error(provider: str, exc: Exception) -> AppError:
    if isinstance(exc, httpx.TimeoutException):
        return AppError(503, "LLM_TIMEOUT", "The AI provider took too long to respond. Please try again.")
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status == 429:
            return AppError(429, "LLM_RATE_LIMITED", "The AI provider is rate limiting requests. Please wait a moment and try again.")
        if status in (401, 403):
            return AppError(503, "LLM_AUTH_ERROR", "The AI provider rejected the configured credentials.")
        return AppError(503, "LLM_PROVIDER_ERROR", f"The AI provider returned an error ({status}).")
    return AppError(503, "LLM_UNAVAILABLE", "The AI provider could not be reached.")


class AnthropicProvider:
    URL = "https://api.anthropic.com/v1/messages"

    def generate(self, system: str, messages: list[dict]) -> str:
        if not settings.llm_api_key:
            raise _not_configured("LLM_API_KEY is empty.")
        if not settings.llm_model:
            raise _not_configured("LLM_MODEL is empty.")
        try:
            resp = httpx.post(
                self.URL,
                headers={"x-api-key": settings.llm_api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": settings.llm_model, "max_tokens": settings.llm_max_tokens, "system": system, "messages": messages},
                timeout=settings.llm_timeout_seconds,
            )
            resp.raise_for_status()
            blocks = resp.json().get("content", [])
            return "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
        except httpx.HTTPError as exc:
            raise _http_error("anthropic", exc) from exc


class OpenAICompatibleProvider:
    """Any API that speaks the OpenAI chat-completions format: OpenAI itself, or a local server such as Ollama
    (which needs no API key)."""

    def __init__(self, *, key_required: bool = True, default_base: str = "https://api.openai.com/v1", name: str = "openai"):
        self.key_required = key_required
        self.default_base = default_base
        self.name = name

    def generate(self, system: str, messages: list[dict]) -> str:
        if self.key_required and not settings.llm_api_key:
            raise _not_configured("LLM_API_KEY is empty.")
        if not settings.llm_model:
            raise _not_configured("LLM_MODEL is empty.")
        base = (settings.llm_base_url or self.default_base).rstrip("/")
        headers = {"Authorization": f"Bearer {settings.llm_api_key}"} if settings.llm_api_key else {}
        payload = {
            "model": settings.llm_model,
            "max_tokens": settings.llm_max_tokens,
            "temperature": settings.llm_temperature,
            "messages": [{"role": "system", "content": system}, *messages],
        }
        if settings.llm_frequency_penalty:
            # Discourages the repetition loops that small local models sometimes fall into.
            payload["frequency_penalty"] = settings.llm_frequency_penalty
        try:
            resp = httpx.post(
                f"{base}/chat/completions",
                headers=headers,
                json=payload,
                timeout=settings.llm_timeout_seconds,
            )
            resp.raise_for_status()
            return (resp.json()["choices"][0]["message"]["content"] or "").strip()
        except httpx.HTTPError as exc:
            raise _http_error(self.name, exc) from exc
        except (KeyError, IndexError, ValueError) as exc:
            raise AppError(503, "LLM_PROVIDER_ERROR", "The AI provider returned an unexpected response.") from exc


_STOPWORDS = {
    "what", "which", "who", "whom", "whose", "when", "where", "why", "how", "does", "did", "have", "has", "had", "this", "that",
    "these", "those", "there", "their", "them", "they", "with", "from", "about", "into", "your", "you", "the", "and", "for", "are",
    "was", "were", "can", "could", "would", "should", "tell", "give", "show", "list", "her", "his", "she", "him", "its", "all", "any",
    "document", "documents", "file", "files", "pdf",
}
_GENERIC = re.compile(r"\b(summari[sz]e|summary|overview|tell me about|what is (this|the|my)|describe)\b", re.I)


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) >= 3 and w not in _STOPWORDS}


class MockProvider:
    """Development-only. Quotes the retrieved passage that shares the most words with the question (or the first
    passage for generic requests like "summarize"), and reports insufficient evidence when nothing overlaps.
    It does not understand meaning, so it is far weaker than a real model."""

    def generate(self, system: str, messages: list[dict]) -> str:
        prompt = messages[-1]["content"] if messages else ""
        question_match = re.search(r"Question:\s*(.+?)(?:\n\nAnswer using only|\Z)", prompt, re.S)
        question = question_match.group(1).strip() if question_match else ""
        sources = re.findall(r"\[S(\d+)\][^\n]*\n(.+?)(?=\n\n\[S\d+\]|\n\nQuestion:)", prompt, re.S)
        if not sources:
            return "INSUFFICIENT_EVIDENCE"

        wanted = _words(question)
        best_number, best_text, best_overlap = sources[0][0], sources[0][1], 0
        for number, text in sources:
            overlap = len(wanted & _words(text))
            if overlap > best_overlap:
                best_number, best_text, best_overlap = number, text, overlap
        if best_overlap == 0 and not _GENERIC.search(question):
            return "INSUFFICIENT_EVIDENCE"
        passage = best_text.strip()[:240]
        return f'{MOCK_PREFIX} The closest passage says: "{passage}" [S{best_number}]'


def get_llm() -> LLMProvider:
    provider = settings.llm_provider.lower()
    if provider == "anthropic":
        return AnthropicProvider()
    if provider in ("openai", "openai_compatible"):
        return OpenAICompatibleProvider()
    if provider == "ollama":
        # Free, local, no key. Install Ollama, run `ollama pull <model>` and set LLM_MODEL to that model.
        return OpenAICompatibleProvider(key_required=False, default_base="http://127.0.0.1:11434/v1", name="ollama")
    if provider == "mock":
        return MockProvider()
    raise _not_configured(f"unknown LLM_PROVIDER '{settings.llm_provider}'.")
