from __future__ import annotations

from collections.abc import Callable

import gradio as gr

from src.server.anki_export import AnkiExportStore, AnkiWord
from src.server.notion_client import NotionClient


MOBILE_UI_CSS = """
.gradio-container {
    max-width: 100% !important;
    padding: 0 !important;
    background: #ffffff !important;
}

.gradio-container > .contain {
    border: 0 !important;
    box-shadow: none !important;
    background: #ffffff !important;
}

#clipboard-input,
#translation-output {
    border: 1px solid var(--border-color-primary) !important;
    border-radius: 8px !important;
    background: var(--background-fill-primary) !important;
}

#clipboard-input {
    margin-bottom: 16px !important;
}

#clipboard-input textarea,
#translation-output textarea {
    border: 0 !important;
    box-shadow: none !important;
}

#translation-output textarea {
    line-height: 1.65 !important;
    max-height: calc(100vh - 120px) !important;
    overflow-y: auto !important;
    resize: none !important;
}

/* Row-level selection for the words table: suppress cell highlight, show full-row highlight */
#words-table table td.selected {
    background: transparent !important;
    outline: none !important;
}
#words-table table tr.selected td,
#words-table table tr:has(td.selected) td {
    background: var(--color-accent-soft, rgba(99, 102, 241, 0.15)) !important;
}
"""


CLIPBOARD_POLL_JS = """
function() {
    let lastClipboard = null;
    let pollInProgress = false;

    const readClipboard = async () => {
        if (typeof AndroidBridge !== "undefined") {
            try {
                return AndroidBridge.getClipboardText();
            } catch (error) {
                console.error("Android clipboard read failed:", error);
                return null;
            }
        }

        if (navigator.clipboard && navigator.clipboard.readText) {
            try {
                return await navigator.clipboard.readText();
            } catch (error) {
                return null;
            }
        }

        return null;
    };

    const pollClipboard = async () => {
        if (pollInProgress) {
            return;
        }
        pollInProgress = true;

        try {
            const clipboardText = await readClipboard();

            if (typeof clipboardText !== "string" || !clipboardText.trim() || clipboardText === lastClipboard) {
                return;
            }

            const input = document.querySelector("#clipboard-input textarea, #clipboard-input input");
            const submit = document.querySelector("#clipboard-input button");
            if (!input || !submit) {
                return;
            }

            lastClipboard = clipboardText;
            const valueSetter = Object.getOwnPropertyDescriptor(
                input instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype,
                "value"
            ).set;
            valueSetter.call(input, clipboardText);
            input.dispatchEvent(new Event("input", { bubbles: true }));
            input.dispatchEvent(new Event("change", { bubbles: true }));
            submit.click();
        } finally {
            pollInProgress = false;
        }
    };

    document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "visible") {
            pollClipboard();
        }
    });
    window.addEventListener("focus", pollClipboard);

    if (document.visibilityState === "visible") {
        pollClipboard();
    }
}
"""


SUBMIT_CLIPBOARD_JS = """
async function(currentText) {
    let clipboardText = null;

    if (typeof AndroidBridge !== "undefined") {
        try {
            clipboardText = AndroidBridge.getClipboardText();
        } catch (error) {
            console.error("Android clipboard read failed:", error);
        }
    } else if (navigator.clipboard && navigator.clipboard.readText) {
        try {
            clipboardText = await navigator.clipboard.readText();
        } catch (error) {
            console.error("Browser clipboard read failed:", error);
        }
    }

    if (typeof clipboardText !== "string" || !clipboardText.trim()) {
        return currentText;
    }

    const input = document.querySelector("#clipboard-input textarea, #clipboard-input input");
    if (input) {
        const valueSetter = Object.getOwnPropertyDescriptor(
            input instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype,
            "value"
        ).set;
        valueSetter.call(input, clipboardText);
        input.dispatchEvent(new Event("input", { bubbles: true }));
        input.dispatchEvent(new Event("change", { bubbles: true }));
    }
    return clipboardText;
}
"""


AUTO_RESIZE_OUTPUT_JS = """
function() {
    const resizeOutput = () => {
        const output = document.querySelector("#translation-output textarea");
        if (!output) {
            return;
        }

        output.style.height = "auto";
        const availableHeight = Math.max(
            160,
            window.innerHeight - output.getBoundingClientRect().top - 16
        );
        const nextHeight = Math.min(output.scrollHeight, availableHeight);
        output.style.height = `${nextHeight}px`;
        output.style.overflowY = output.scrollHeight > availableHeight ? "auto" : "hidden";
    };

    window.addEventListener("resize", resizeOutput);
    window.setInterval(resizeOutput, 250);
    resizeOutput();
}
"""


# Reads (or creates) a persistent random client ID from browser localStorage.
# This ID survives page refreshes, tab closes, and app restarts — uniquely
# identifying each user's Anki word list on the server without requiring login.
CLIENT_ID_JS = """
function() {
    let id = localStorage.getItem("anki_client_id");
    if (!id || !id.trim()) {
        id = "c_" + Math.random().toString(36).substring(2, 10) + "_" + Date.now().toString(36);
        localStorage.setItem("anki_client_id", id);
    }
    return id;
}
"""


def create_demo(
    translate_fn: Callable[[str], object],
    anki_store: AnkiExportStore | None = None,
    notion_client: NotionClient | None = None,
) -> gr.Blocks:
    export_store = anki_store or AnkiExportStore()
    notion_store = notion_client or NotionClient()

    def format_result(result: object) -> str:
        return (
            f"{result.japanese_with_furigana.strip()}\n\n"
            f"{result.translation.strip()}\n\n"
            f"【语法骨架】\n{result.structure_anchor.strip()}"
        )

    def translate_and_format(text: str) -> tuple[str, list[list[str]]]:
        result = translate_fn(text)
        words = [
            [word.surface, word.dictionary_form, word.reading, word.definition, word.grammar_note]
            for word in result.words_lemmatized
        ]
        return format_result(result), words

    def _resolve_client_id(client_id: str, request: gr.Request | None) -> str:
        """Prefer the localStorage client_id; fall back to session_hash if empty."""
        safe_id = (client_id or "").strip()
        if not safe_id and request:
            safe_id = getattr(request, "session_hash", "") or ""
        return safe_id or "default"

    def add_selected_word(
        words: list[list[str]], client_id: str, event: gr.SelectData, request: gr.Request = None
    ) -> str:
        row_index, _ = event.index
        if row_index >= len(words):
            return "未找到所选词条。"
        surface, dictionary_form, reading, definition, grammar_note = words[row_index]
        word = AnkiWord(surface, dictionary_form, reading, definition, grammar_note)
        safe_id = _resolve_client_id(client_id, request)
        anki_added = export_store.add_word(safe_id, word)
        count = export_store.get_pending_count(safe_id)
        anki_message = "已加入 Anki" if anki_added else "Anki 已存在，未重复加入"

        try:
            notion_result = notion_store.save_word(word)
            notion_messages = {
                "added": "Notion DB 添加成功",
                "exists": "Notion DB 已存在，未重复添加",
                "disabled": "Notion DB 未配置",
            }
            notion_message = notion_messages.get(notion_result.status, "Notion DB 未同步")
        except Exception as error:
            print(
                f"[notion] save failed in click handler: {type(error).__name__}: {error}",
                flush=True,
            )
            notion_message = "Notion DB 添加失败"

        return (
            f"{anki_message}；{notion_message}：**{dictionary_form}（{reading}）**"
            f"（当前共 {count} 个待导出）"
        )

    def save_selected_word_to_notion(words: list[list[str]], event: gr.SelectData) -> str:
        row_index, _ = event.index
        if row_index >= len(words):
            return "未找到所选词条。"
        surface, dictionary_form, reading, definition, grammar_note = words[row_index]
        word = AnkiWord(surface, dictionary_form, reading, definition, grammar_note)

        try:
            notion_result = notion_store.save_word(word)
            notion_messages = {
                "added": "Notion DB 添加成功",
                "exists": "Notion DB 已存在，未重复添加",
                "disabled": "Notion DB 未配置",
            }
            notion_message = notion_messages.get(notion_result.status, "Notion DB 未同步")
        except Exception as error:
            print(
                f"[notion] save failed in click handler: {type(error).__name__}: {error}",
                flush=True,
            )
            notion_message = "Notion DB 添加失败"

        return f"{notion_message}：**{dictionary_form}（{reading}）**"

    def download_anki(client_id: str, request: gr.Request = None) -> tuple[object, str]:
        safe_id = _resolve_client_id(client_id, request)
        export_path = export_store.export_and_clear(safe_id)
        if export_path is None:
            return gr.File(value=None, visible=False), "还没有加入任何单词。"
        return (
            gr.File(value=str(export_path), visible=True),
            "Anki 文件已生成。点击下方文件名下载；待下载列表已清空（0 个待导出）。",
        )

    def refresh_pending_status(client_id: str, request: gr.Request = None) -> str:
        safe_id = _resolve_client_id(client_id, request)
        count = export_store.get_pending_count(safe_id)
        if count > 0:
            return f"当前暂存待导出词条：**{count}** 个（可继续点击表格中的生词添加，或点击按钮生成下载）"
        return "当前待导出列表为空（点击上方表格中的生词即可加入）。"

    with gr.Blocks(title="日文振假名翻译工具") as demo:
        text_input = gr.Textbox(
            show_label=False,
            placeholder="输入日文",
            lines=3,
            max_lines=8,
            elem_id="clipboard-input",
            submit_btn="🔍",
        )

        result_output = gr.Textbox(
            show_label=False,
            lines=8,
            max_lines=100,
            interactive=False,
            elem_id="translation-output",
        )
        word_rows = gr.State([])
        words_table = gr.Dataframe(
            headers=["原文", "原形", "读音", "释义", "词性/语法"],
            datatype=["str", "str", "str", "str", "str"],
            interactive=False,
            label="词汇拆解（点击任一词条加入 Anki）",
            elem_id="words-table",
        )
        notion_status = gr.Markdown()

        text_input.submit(
            translate_and_format,
            text_input,
            [result_output, word_rows],
            js=SUBMIT_CLIPBOARD_JS,
        )
        word_rows.change(lambda words: words, word_rows, words_table)
        words_table.select(save_selected_word_to_notion, word_rows, notion_status)

        demo.load(None, js=CLIPBOARD_POLL_JS)
        demo.load(None, js=AUTO_RESIZE_OUTPUT_JS)
    return demo
