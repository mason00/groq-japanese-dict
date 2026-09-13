from __future__ import annotations

import gradio as gr

from src.client.callbacks import create_callbacks
from src.client.ui_assets import (
    AUTO_RESIZE_OUTPUT_JS,
    CLIPBOARD_POLL_JS,
    MOBILE_UI_CSS,
    NATIVE_PASTE_BUTTON_JS,
)
from src.server.anki_export import AnkiExportStore
from src.server.notion_client import NotionClient


def create_demo(
    translate_fn,
    anki_store: AnkiExportStore | None = None,
    notion_client: NotionClient | None = None,
) -> gr.Blocks:
    callbacks = create_callbacks(
        translate_fn,
        anki_store or AnkiExportStore(),
        notion_client or NotionClient(),
    )

    with gr.Blocks(title="日文振假名翻译工具", css=MOBILE_UI_CSS) as demo:
        with gr.Row(elem_id="clipboard-input"):
            text_input = gr.Textbox(
                show_label=False,
                placeholder="输入日文",
                lines=1,
                max_lines=1,
                scale=1,
                elem_id="text-input",
            )
            submit_btn = gr.Button(
                "🔍",
                elem_id="submit-button",
                scale=0,
                variant="secondary",
                min_width=44,
                size="lg",
            )
            gr.Button(
                "📋",
                elem_id="native-paste-button",
                scale=0,
                variant="secondary",
                min_width=44,
                size="lg",
            )

        result_output = gr.Textbox(
            show_label=False,
            lines=6,
            max_lines=100,
            interactive=False,
            elem_id="translation-output",
        )
        word_rows = gr.State([])
        words_table = gr.Dataframe(
            headers=["原文", "原形", "读音", "释义", "词性/语法"],
            datatype=["str", "str", "str", "str", "str"],
            interactive=False,
            #label="词汇拆解（点击任一词条加入 Anki）",
            elem_id="words-table",
            buttons=[],
        )
        notion_status = gr.Markdown()

        submit_btn.click(
            callbacks["translate_and_format"],
            inputs=text_input,
            outputs=[result_output, word_rows],
        )
        word_rows.change(lambda words: words, word_rows, words_table)
        words_table.select(
            callbacks["save_selected_word_to_notion"],
            [word_rows, result_output],
            notion_status,
        )

        demo.load(None, js=CLIPBOARD_POLL_JS)
        demo.load(None, js=AUTO_RESIZE_OUTPUT_JS)
        demo.load(None, js=NATIVE_PASTE_BUTTON_JS)
    return demo
