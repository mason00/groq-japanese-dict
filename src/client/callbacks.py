"""Callbacks used by the Gradio client UI."""

from collections.abc import Callable

import gradio as gr

from src.server.anki_export import AnkiExportStore, AnkiWord
from src.server.notion_client import NotionClient, VocabularyCard


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


def create_card_callbacks(notion_client: NotionClient) -> dict[str, Callable[..., object]]:
    def card_display(card: VocabularyCard, revealed: bool) -> tuple[str, str]:
        details = ""
        if revealed:
            details = "\n\n".join(
                value
                for value in [
                    f"**读音**\n{card.reading}" if card.reading else "",
                    f"**释义**\n{card.meaning}" if card.meaning else "",
                    f"**例句**\n{card.example}" if card.example else "",
                    f"**翻译**\n{card.translation}" if card.translation else "",
                ]
                if value
            )
        return card.word, details

    def navigation_updates(index: int, count: int) -> tuple[object, object]:
        return (
            gr.Button("Previous", interactive=index > 0),
            gr.Button("Next", interactive=index < count - 1),
        )

    def card_updates(
        cards: list[VocabularyCard], index: int
    ) -> tuple[int, object, str, str, str, object, object]:
        if not cards:
            previous, next_card = navigation_updates(0, 0)
            return 0, gr.Button("Notion 词汇库为空。", interactive=False), "", "0 / 0", "", previous, next_card

        word, details = card_display(cards[index], revealed=False)
        previous, next_card = navigation_updates(index, len(cards))
        return (
            index,
            gr.Button(word, interactive=True),
            details,
            f"{index + 1} / {len(cards)}",
            str(index + 1),
            previous,
            next_card,
        )

    def load_cards() -> tuple[list[VocabularyCard], int, object, str, str, str, object, object]:
        try:
            cards = notion_client.list_vocabulary_cards()
        except Exception as error:
            print(f"[notion] card load failed: {error}", flush=True)
            cards = []
            message = "无法读取 Notion 词汇库。"
        else:
            message = "Notion 词汇库为空。" if not cards else ""

        if not cards:
            previous, next_card = navigation_updates(0, 0)
            return cards, 0, gr.Button(message, interactive=False), "", "0 / 0", "", previous, next_card

        index, word, details, counter, position, previous, next_card = card_updates(cards, 0)
        return cards, index, word, details, counter, position, previous, next_card

    def reveal_card(cards: list[VocabularyCard], index: int) -> str:
        if not cards:
            return ""
        _, details = card_display(cards[index], revealed=True)
        return details

    def change_card(
        cards: list[VocabularyCard], index: int, direction: int
    ) -> tuple[int, object, str, str, str, object, object]:
        if not cards:
            return card_updates(cards, 0)
        next_index = min(max(index + direction, 0), len(cards) - 1)
        return card_updates(cards, next_index)

    def go_to_card(
        cards: list[VocabularyCard], index: int, position: str
    ) -> tuple[int, object, str, str, str, object, object]:
        if not cards:
            return card_updates(cards, 0)
        try:
            requested_position = int(position)
        except (TypeError, ValueError):
            return card_updates(cards, index)
        if not 1 <= requested_position <= len(cards):
            return card_updates(cards, index)
        return card_updates(cards, requested_position - 1)

    return {
        "load_cards": load_cards,
        "reveal_card": reveal_card,
        "previous_card": lambda cards, index: change_card(cards, index, -1),
        "next_card": lambda cards, index: change_card(cards, index, 1),
        "go_to_card": go_to_card,
    }