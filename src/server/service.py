from __future__ import annotations

from .llm_client import create_llm_client
from .pipeline import JapanesePipeline


pipeline = JapanesePipeline(create_llm_client())


def translate_text(text: str) -> tuple[str, str, str, str]:
    return pipeline.process(text)
