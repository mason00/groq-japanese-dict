from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .llm_client import create_llm_client
from .pipeline import JapanesePipeline


class TranslateRequest(BaseModel):
    text: str = Field(min_length=1, description="要翻译的日文")


class TranslateResponse(BaseModel):
    japanese_with_furigana: str
    words: str
    translation: str
    difficult_words: str


pipeline = JapanesePipeline(create_llm_client())
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
    japanese_with_furigana, words, translation, difficult_words = pipeline.process(request.text)
    return TranslateResponse(
        japanese_with_furigana=japanese_with_furigana,
        words=words,
        translation=translation,
        difficult_words=difficult_words,
    )