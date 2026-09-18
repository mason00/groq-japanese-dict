import unittest
from unittest.mock import MagicMock

import gradio as gr

from src.client.callbacks import create_card_callbacks, create_callbacks
from src.server.anki_export import AnkiWord
from src.server.notion_client import VocabularyCard


class CallbacksTests(unittest.TestCase):
    def setUp(self) -> None:
        self.translate_fn = MagicMock()
        self.export_store = MagicMock()
        self.notion_client = MagicMock()
        self.callbacks = create_callbacks(
            self.translate_fn, self.export_store, self.notion_client
        )

    def test_save_selected_word_to_notion_extracts_translation(self) -> None:
        words = [["食べた", "食べる", "たべる", "吃", "動詞"]]
        formatted_output = "食べた（たべた）\n\n吃了饭\n\n【语法骨架】\n..."
        event = MagicMock(spec=gr.SelectData)
        event.index = (0, 0)

        notion_result = MagicMock()
        notion_result.status = "added"
        self.notion_client.save_word.return_value = notion_result

        save_fn = self.callbacks["save_selected_word_to_notion"]
        res = save_fn(words, formatted_output, event)

        self.assertIn("Notion DB 添加成功", res)
        self.notion_client.save_word.assert_called_once()
        saved_word: AnkiWord = self.notion_client.save_word.call_args[0][0]
        self.assertEqual(saved_word.surface, "食べた")
        self.assertEqual(saved_word.dictionary_form, "食べる")
        self.assertEqual(saved_word.reading, "たべる")
        self.assertEqual(saved_word.definition, "吃")
        self.assertEqual(saved_word.grammar_note, "食べた（たべた）")
        self.assertEqual(saved_word.translation, "吃了饭")

    def test_card_callbacks_reveal_and_navigate(self) -> None:
        notion_client = MagicMock()
        notion_client.list_vocabulary_cards.return_value = [
            VocabularyCard("飲む", "のむ", "喝", "水を飲む。", "I drink.", "2026-02-01"),
            VocabularyCard("食べる", "たべる", "吃", "ご飯を食べる。", "I eat.", "2026-01-01"),
        ]
        callbacks = create_card_callbacks(notion_client)

        cards, index, word, details, counter, previous, next_card = callbacks["load_cards"]()

        self.assertEqual((index, word.value, details, counter), (0, "飲む", "", "1 / 2"))
        self.assertFalse(previous.interactive)
        self.assertTrue(next_card.interactive)
        self.assertIn("**读音**\nのむ", callbacks["reveal_card"](cards, index))

        index, word, details, counter, previous, next_card = callbacks["next_card"](cards, index)

        self.assertEqual((index, word.value, details, counter), (1, "食べる", "", "2 / 2"))
        self.assertTrue(previous.interactive)
        self.assertFalse(next_card.interactive)
        self.assertEqual(callbacks["next_card"](cards, index)[0], 1)

    def test_card_callbacks_return_empty_state_after_load_failure(self) -> None:
        notion_client = MagicMock()
        notion_client.list_vocabulary_cards.side_effect = RuntimeError("missing configuration")

        _, index, word, details, counter, previous, next_card = create_card_callbacks(notion_client)["load_cards"]()

        self.assertEqual((index, word.value, details, counter), (0, "无法读取 Notion 词汇库。", "", "0 / 0"))
        self.assertFalse(previous.interactive)
        self.assertFalse(next_card.interactive)


if __name__ == "__main__":
    unittest.main()

