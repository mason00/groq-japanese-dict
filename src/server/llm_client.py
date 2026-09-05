from __future__ import annotations

import json
import os
import ssl
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import tiktoken
import httpx
import truststore
from tenacity import (
    Retrying,
    retry_if_exception_type,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential,
)


@dataclass(frozen=True)
class LLMResponse:
    content: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class TokenCounter:
    def __init__(self) -> None:
        try:
            self._encoding = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self._encoding = None

    def count(self, text: str) -> int:
        if self._encoding is not None:
            return len(self._encoding.encode(text))
        return max(1, (len(text) + 3) // 4)


class LLMClient(ABC):
    def __init__(self, model: str, timeout: float, max_retries: int) -> None:
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.token_counter = TokenCounter()

    def _with_retry(self, request: Any, *args: Any) -> Any:
        retrying = Retrying(
            retry=retry_if_exception_type(Exception)
            & retry_if_not_exception_type(self._bad_request_error_type()),
            wait=wait_exponential(multiplier=1, min=1, max=8),
            stop=stop_after_attempt(self.max_retries),
            reraise=True,
        )
        return retrying(request, *args)

    @staticmethod
    def _bad_request_error_type() -> type[Exception]:
        try:
            from groq import BadRequestError

            return BadRequestError
        except ImportError:
            return ValueError

    @abstractmethod
    def complete(self, text: str, system_prompt: str) -> LLMResponse:
        raise NotImplementedError


class GroqClient(LLMClient):
    def __init__(self, model: str, timeout: float, max_retries: int) -> None:
        from groq import Groq

        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY 环境变量未设置")
        super().__init__(model, timeout, max_retries)
        ssl_context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        http_client = httpx.Client(verify=ssl_context, timeout=timeout)
        self._client = Groq(api_key=api_key, timeout=timeout, http_client=http_client)

    def _request_once(self, text: str, system_prompt: str) -> Any:
        return self._client.chat.completions.create(
            model=self.model,
            max_completion_tokens=int(os.getenv("LLM_MAX_COMPLETION_TOKENS", "512")),
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
        )

    def complete(self, text: str, system_prompt: str) -> LLMResponse:
        response = self._with_retry(self._request_once, text, system_prompt)
        content = response.choices[0].message.content or ""
        usage = response.usage
        prompt_tokens = getattr(usage, "prompt_tokens", 0) or self.token_counter.count(
            system_prompt + text
        )
        completion_tokens = getattr(usage, "completion_tokens", 0) or self.token_counter.count(content)
        return LLMResponse(content, prompt_tokens, completion_tokens, prompt_tokens + completion_tokens)


class OllamaClient(LLMClient):
    def __init__(self, model: str, timeout: float, max_retries: int, base_url: str) -> None:
        super().__init__(model, timeout, max_retries)
        self.base_url = base_url.rstrip("/")

    def _request_once(self, text: str, system_prompt: str) -> dict[str, Any]:
        payload = json.dumps(
            {
                "model": self.model,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0},
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def complete(self, text: str, system_prompt: str) -> LLMResponse:
        response = self._with_retry(self._request_once, text, system_prompt)
        content = response.get("message", {}).get("content", "")
        prompt_tokens = response.get("prompt_eval_count") or self.token_counter.count(system_prompt + text)
        completion_tokens = response.get("eval_count") or self.token_counter.count(content)
        return LLMResponse(content, prompt_tokens, completion_tokens, prompt_tokens + completion_tokens)


def create_llm_client() -> LLMClient:
    provider = os.getenv("LLM_PROVIDER", "groq").lower()
    timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "30"))
    max_retries = max(1, int(os.getenv("LLM_MAX_RETRIES", "3")))

    if provider == "groq":
        return GroqClient(os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b"), timeout, max_retries)
    if provider == "ollama":
        return OllamaClient(
            os.getenv("OLLAMA_MODEL", "qwen3:8b"),
            timeout,
            max_retries,
            os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        )
    raise ValueError(f"不支持的 LLM_PROVIDER: {provider}，可选值为 groq 或 ollama")