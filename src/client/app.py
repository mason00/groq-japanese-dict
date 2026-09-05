from __future__ import annotations

from collections.abc import Callable

import gradio as gr


def create_demo(
    translate_fn: Callable[[str], tuple[str, str, str, str]],
) -> gr.Interface:
    return gr.Interface(
        fn=translate_fn,
        inputs=gr.Textbox(label="输入日文"),
        outputs=[
            gr.Textbox(label="AI 返回的振假名日语"),
            gr.Textbox(label="分词单词列表"),
            gr.Textbox(label="中文翻译"),
            gr.Textbox(label="N4 以上难词翻译"),
        ],
        title="日文振假名翻译工具",
    )
