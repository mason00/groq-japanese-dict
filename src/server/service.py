from __future__ import annotations

from .llm_client import create_llm_client
from .pipeline import JapanesePipeline


def translate_text(text: str) -> tuple[str, str, str, str]:
    pipeline = JapanesePipeline(create_llm_client())
    return pipeline.process(text)
