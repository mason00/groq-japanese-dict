from __future__ import annotations

import gradio as gr

from ..server.service import translate_text

try:
    import spaces  # type: ignore[import-not-found]
except ImportError:
    class _LocalSpaces:
        @staticmethod
        def GPU(function):
            return function

    spaces = _LocalSpaces()


@spaces.GPU
def _translate(text: str) -> tuple[str, str, str, str]:
    return translate_text(text)


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
