from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .pipeline import LemmatizedWord
from .service import translate_text


class TranslateRequest(BaseModel):
    text: str = Field(min_length=1, description="要翻译的日文")


class TranslateResponse(BaseModel):
    translation: str
    japanese_with_furigana: str
    structure_anchor: str
    words_lemmatized: list[LemmatizedWord]


app = FastAPI(
    title="日文振假名翻译 API",
    version="1.0.0",
    description="使用统一 LLM 客户端生成带振假名日语和中文翻译。",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/translate", response_model=TranslateResponse)
def translate(request: TranslateRequest) -> TranslateResponse:
    result = translate_text(request.text)
    return TranslateResponse(
        translation=result.translation,
        japanese_with_furigana=result.japanese_with_furigana,
        structure_anchor=result.structure_anchor,
        words_lemmatized=result.words_lemmatized,
    )