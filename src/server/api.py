from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .notion_client import NotionClient
from .pipeline import LemmatizedWord
from .service import translate_text


class TranslateRequest(BaseModel):
    text: str = Field(min_length=1, description="要翻译的日文")


class TranslateResponse(BaseModel):
    translation: str
    japanese_with_furigana: str
    structure_anchor: str
    words_lemmatized: list[LemmatizedWord]


class CardResponse(BaseModel):
    word: str
    reading: str
    meaning: str
    example: str
    translation: str
    created_time: str


app = FastAPI(
    title="日文振假名翻译 API",
    version="1.0.0",
    description="使用统一 LLM 客户端生成带振假名日语和中文翻译。",
)
notion_client = NotionClient()
frontend_origins = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", "*").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.get("/card", response_model=list[CardResponse])
def cards() -> list[CardResponse]:
    return [
        CardResponse(
            word=card.word,
            reading=card.reading,
            meaning=card.meaning,
            example=card.example,
            translation=card.translation,
            created_time=card.created_time,
        )
        for card in notion_client.list_vocabulary_cards()
    ]


frontend_path = Path(__file__).resolve().parents[1] / "react" / "dist"
if frontend_path.is_dir():
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")