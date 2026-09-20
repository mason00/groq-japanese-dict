from __future__ import annotations

from threading import Lock

from .llm_client import create_llm_client
from .pipeline import JapanesePipeline, TranslationResponse


_pipeline: JapanesePipeline | None = None
_pipeline_lock = Lock()


def _get_pipeline() -> JapanesePipeline:
    global _pipeline
    if _pipeline is None:
        with _pipeline_lock:
            if _pipeline is None:
                _pipeline = JapanesePipeline(create_llm_client())
    return _pipeline


def translate_text(text: str) -> TranslationResponse:
    return _get_pipeline().process(text)
