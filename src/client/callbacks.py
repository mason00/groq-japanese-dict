"""Callbacks used by the Gradio client UI."""

from collections.abc import Callable

import gradio as gr

from src.server.anki_export import AnkiExportStore, AnkiWord
from src.server.notion_client import NotionClient


def create_callbacks(
    translate_fn: Callable[[str], object],
    export_store: AnkiExportStore,
    notion_store: NotionClient,
) -> dict[str, Callable[..., object]]:
    def translate_and_format(text: str) -> tuple[str, list[list[str]]]:
        result = translate_fn(text)
        words = [
            [word.surface, word.dictionary_form, word.reading, word.definition, word.grammar_note]
            for word in result.words_lemmatized
        ]
        formatted = (
            f"{result.japanese_with_furigana.strip()}\n\n"
            f"{result.translation.strip()}\n\n"
            f"【语法骨架】\n{result.structure_anchor.strip()}"
        )
        return formatted, words

    def resolve_client_id(client_id: str, request: gr.Request | None) -> str:
        safe_id = (client_id or "").strip()
        if not safe_id and request:
            safe_id = getattr(request, "session_hash", "") or ""
        return safe_id or "default"

    def save_selected_word_to_notion(
        words: list[list[str]], formatted_output: str, event: gr.SelectData
    ) -> str:
        row_index, _ = event.index
        if row_index >= len(words):
            return "未找到所选词条。"
        surface, dictionary_form, reading, definition, grammar_note = words[row_index]
        parts = formatted_output.split("\n\n") if formatted_output else []
        example = parts[0].strip() if len(parts) > 0 and parts[0].strip() else grammar_note
        translation = parts[1].strip() if len(parts) > 1 else ""
        word = AnkiWord(surface, dictionary_form, reading, definition, example, translation)
        try:
            notion_result = notion_store.save_word(word)
            messages = {"added": "Notion DB 添加成功", "exists": "Notion DB 已存在，未重复添加", "disabled": "Notion DB 未配置"}
            status = messages.get(notion_result.status, "Notion DB 未同步")
        except Exception as error:
            print(f"[notion] save failed: {error}", flush=True)
            status = "Notion DB 添加失败"
        return f"{status}：**{dictionary_form}（{reading}）**"

    def download_anki(client_id: str, request: gr.Request = None) -> tuple[object, str]:
        safe_id = resolve_client_id(client_id, request)
        export_path = export_store.export_and_clear(safe_id)
        if export_path is None:
            return gr.File(value=None, visible=False), "还没有加入任何单词。"
        return gr.File(value=str(export_path), visible=True), "Anki 文件已生成。"

    def refresh_pending_status(client_id: str, request: gr.Request = None) -> str:
        count = export_store.get_pending_count(resolve_client_id(client_id, request))
        return f"当前暂存待导出词条：**{count}** 个" if count else "当前待导出列表为空。"

    return {
        "translate_and_format": translate_and_format,
        "save_selected_word_to_notion": save_selected_word_to_notion,
        "download_anki": download_anki,
        "refresh_pending_status": refresh_pending_status,
    }