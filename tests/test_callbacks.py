import unittest
from unittest.mock import MagicMock

import gradio as gr

from src.client.callbacks import create_callbacks
from src.server.anki_export import AnkiWord


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


if __name__ == "__main__":
    unittest.main()

