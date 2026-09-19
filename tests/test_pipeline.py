from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from src.server.llm_client import LLMClient, LLMResponse
from src.server.pipeline import JapanesePipeline, TranslationResponse


class PipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_llm = MagicMock(spec=LLMClient)
        self.pipeline = JapanesePipeline(self.mock_llm)

    def test_extract_morphemes(self) -> None:
        sentence = "さすがに新入生の五年生はきまじめな顔をして校門をくぐった。"
        morphemes, ref = self.pipeline._extract_morphemes(sentence)

        # Ensure punctuation is filtered out
        self.assertNotIn("。", ref)
        self.assertTrue(all(m.surface != "。" for m in morphemes))

        # Check numbered IDs
        self.assertGreater(len(morphemes), 0)
        self.assertEqual(morphemes[0].id, 1)
        self.assertIn("1. 表面:", ref)

        # Check key components in reference text
        self.assertIn("表面: 新入生", ref)
        self.assertIn("原型: 新入生", ref)
        self.assertIn("读音: しんにゅうせい", ref)
        self.assertIn("JMdict英文参考:", ref)

        # Check hiragana conversion
        self.assertNotIn("シンニュウセイ", ref)
        self.assertNotIn("クグッタ", ref)

    def test_format_prompt_contains_reference_and_text(self) -> None:
        sentence = "日本語を勉強します。"
        _, ref = self.pipeline._extract_morphemes(sentence)
        prompt = self.pipeline._format_prompt(sentence, ref)

        self.assertIn("[本地词汇与JMdict参考]", prompt)
        self.assertIn("用户输入的日文：日本語を勉強します。", prompt)
        self.assertIn("word_explanations", prompt)

    def test_process_with_mock_llm_and_merge(self) -> None:
        mock_json = """
        {
            "translation": "学习日语。",
            "japanese_with_furigana": "日本語（にほんご）を勉強（べんきょう）します。",
            "structure_anchor": "核心谓语：勉強します",
            "word_explanations": [
                {"id": 1, "definition": "日语", "grammar_note": "名詞"},
                {"id": 2, "definition": "宾格助词", "grammar_note": "格助詞"},
                {"id": 3, "definition": "学习", "grammar_note": "動詞/サ変"}
            ]
        }
        """
        self.mock_llm.complete.return_value = LLMResponse(
            content=mock_json,
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
        )

        result = self.pipeline.process("日本語を勉強します。")

        self.assertIsInstance(result, TranslationResponse)
        self.assertEqual(result.translation, "学习日语。")
        self.assertEqual(result.japanese_with_furigana, "日本語（にほんご）を勉強（べんきょう）します。")
        self.assertEqual(result.structure_anchor, "核心谓语：勉強します")

        # Verify that words_lemmatized contains the full fields merged from local + LLM
        self.assertGreaterEqual(len(result.words_lemmatized), 3)
        first_word = result.words_lemmatized[0]
        self.assertEqual(first_word.surface, "日本語")
        self.assertEqual(first_word.dictionary_form, "日本語")
        self.assertEqual(first_word.reading, "にほんご")
        self.assertEqual(first_word.definition, "日语")
        self.assertEqual(first_word.grammar_note, "名詞")

    def test_merge_fallback_on_missing_id(self) -> None:
        # LLM only returns explanation for word id 1, missing id 2 and 3
        mock_json = """
        {
            "translation": "学习日语。",
            "japanese_with_furigana": "日本語（にほんご）を勉強（べんきょう）します。",
            "structure_anchor": "核心谓语：勉強します",
            "word_explanations": [
                {"id": 1, "definition": "日语", "grammar_note": "名詞"}
            ]
        }
        """
        self.mock_llm.complete.return_value = LLMResponse(
            content=mock_json,
            prompt_tokens=100,
            completion_tokens=30,
            total_tokens=130,
        )

        result = self.pipeline.process("日本語を勉強します。")
        self.assertIsInstance(result, TranslationResponse)
        # Should gracefully fallback for words without LLM explanation
        self.assertGreaterEqual(len(result.words_lemmatized), 2)
        second_word = result.words_lemmatized[1]
        self.assertEqual(second_word.surface, "を")
        self.assertEqual(second_word.grammar_note, "助詞")

    def test_merge_ignores_placeholder_definition_and_uses_glosses(self) -> None:
        mock_json = """
        {
            "translation": "学习日语。",
            "japanese_with_furigana": "日本語（にほんご）を勉強（べんきょう）します。",
            "structure_anchor": "核心谓语：勉強します",
            "word_explanations": [
                {"id": 1, "definition": "无", "grammar_note": "名詞"}
            ]
        }
        """
        local_morphemes = [
            self.pipeline._extract_morphemes("日本語")[0][0],
        ]
        local_morphemes[0].glosses = ["Japanese language", "language"]

        result = self.pipeline._merge_results(mock_json, local_morphemes)

        self.assertEqual(result.words_lemmatized[0].definition, "Japanese language; language")
        self.assertEqual(result.words_lemmatized[0].meaning, "Japanese language; language")


if __name__ == "__main__":
    unittest.main()
