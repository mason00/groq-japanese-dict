from __future__ import annotations

import os
from pathlib import Path

client_root = Path(__file__).resolve().parent
os.environ["GRADIO_WATCH_DIRS"] = str(client_root)
os.environ["GRADIO_WATCH_DEMO_PATH"] = str(Path(__file__).resolve())
os.environ["GRADIO_WATCH_MODULE_NAME"] = "src.client.app"

import gradio as gr

from .api_client import TranslationApiClient


api_client = TranslationApiClient()


def _translate(text: str) -> tuple[str, str, str, str]:
    result = api_client.translate(text)
    return (
        result.japanese_with_furigana,
        result.words,
        result.translation,
        result.difficult_words,
    )


demo = gr.Interface(
    fn=_translate,
    inputs=gr.Textbox(label="输入日文"),
    outputs=[
        gr.Textbox(label="AI 返回的振假名日语"),
        gr.Textbox(label="分词单词列表"),
        gr.Textbox(label="中文翻译"),
        gr.Textbox(label="N4 以上难词翻译"),
    ],
    title="日文振假名翻译工具",
)


def main() -> None:
    tracing = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
    project = os.getenv("LANGSMITH_PROJECT", "default")
    key_configured = bool(os.getenv("LANGSMITH_API_KEY")) and not os.getenv(
        "LANGSMITH_API_KEY", ""
    ).startswith("PASTE_")
    print(
        f"LangSmith tracing: {'enabled' if tracing else 'disabled'} | "
        f"project={project} | api_key={'configured' if key_configured else 'missing'}",
        flush=True,
    )
    demo.launch(debug=True, show_error=True)


if __name__ == "__main__":
    main()