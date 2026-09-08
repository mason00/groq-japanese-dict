from __future__ import annotations

from .llm_client import create_llm_client
from .pipeline import JapanesePipeline, TranslationResponse


def translate_text(text: str) -> TranslationResponse:
    pipeline = JapanesePipeline(create_llm_client())
    return pipeline.process(text)
