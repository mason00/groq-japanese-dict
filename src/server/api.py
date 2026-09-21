from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .anki_export import AnkiWord

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
class SaveWordRequest(BaseModel):
    surface: str = Field(..., description="原形")
    dictionary_form: str = Field(..., description="词典形")
    reading: str = Field(..., description="假名")
    definition: str = Field(..., description="定义")
    grammar_note: str = Field(..., description="例句")
    translation: str = ""

class SaveWordResponse(BaseModel):
    status: str
    message: str = ""

@app.post("/save_word", response_model=SaveWordResponse)
def save_word(request: SaveWordRequest) -> SaveWordResponse:
    anki_word = AnkiWord(
        surface=request.surface,
        dictionary_form=request.dictionary_form,
        reading=request.reading,
        definition=request.definition,
        grammar_note=request.grammar_note,
        translation=request.translation,
    )
    result = notion_client.save_word(anki_word)
    return SaveWordResponse(status=result.status, message=result.message)


def _extract_limit(request: Request, limit: int | None = None) -> int | None:
    if limit is not None:
        return limit
    for key, value in request.query_params.items():
        key_lower = key.lower()
        if key_lower in ("count", "n", "page_size", "size", "limit"):
            try:
                return int(value)
            except ValueError:
                pass
        if key_lower in ("first", "one"):
            return 1
        if key.isdigit():
            return int(key)
    query = request.url.query.strip().lower()
    if query.isdigit():
        return int(query)
    if query in ("first", "one"):
        return 1
    return None


@app.get("/card", response_model=list[CardResponse])
def cards(
    request: Request,
    limit: int | None = Query(default=20, description="获取卡片数量"),
    offset: int = Query(default=0, ge=0, description="跳过前面的卡片数量"),
) -> list[CardResponse]:
    target_limit = _extract_limit(request, limit)
    if offset:
        cards = notion_client.list_vocabulary_cards(limit=target_limit, offset=offset)
    else:
        cards = notion_client.list_vocabulary_cards(limit=target_limit)
    return [
        CardResponse(
            word=card.word,
            reading=card.reading,
            meaning=card.meaning,
            example=card.example,
            translation=card.translation,
            created_time=card.created_time,
        )
        for card in cards
    ]


frontend_path = Path(__file__).resolve().parents[1] / "react" / "dist"
if frontend_path.is_dir():
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")