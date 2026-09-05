from __future__ import annotations

import os

import httpx
from pydantic import BaseModel


class TranslateResponse(BaseModel):
    japanese_with_furigana: str
    words: str
    translation: str
    difficult_words: str


class TranslationApiClient:
    def __init__(self, base_url: str | None = None, timeout: float | None = None) -> None:
        self.base_url = (base_url or os.getenv("TRANSLATION_API_URL", "http://127.0.0.1:8000")).rstrip("/")
        self.timeout = timeout or float(os.getenv("TRANSLATION_API_TIMEOUT", "60"))

    def translate(self, text: str) -> TranslateResponse:
        try:
            response = httpx.post(
                f"{self.base_url}/translate",
                json={"text": text},
                timeout=self.timeout,
            )
            response.raise_for_status()
            return TranslateResponse.model_validate(response.json())
        except httpx.HTTPError as error:
            raise RuntimeError(f"翻译服务不可用：{self.base_url}") from error
        except ValueError as error:
            raise RuntimeError("翻译服务返回的数据格式无效") from error