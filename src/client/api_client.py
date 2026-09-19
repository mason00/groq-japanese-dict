from __future__ import annotations

import os

import httpx
from pydantic import BaseModel


class LemmatizedWord(BaseModel):
    word: str | None = None
    reading: str
    meaning: str | None = None
    example: str | None = None
    translation: str | None = None
    surface: str | None = None
    dictionary_form: str | None = None
    definition: str | None = None
    grammar_note: str | None = None


class TranslateResponse(BaseModel):
    translation: str
    japanese_with_furigana: str
    structure_anchor: str
    words_lemmatized: list[LemmatizedWord]


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