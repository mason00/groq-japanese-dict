import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from src.server.api import app
from src.server.notion_client import VocabularyCard


class ApiTests(unittest.TestCase):
    def test_card_returns_vocabulary_cards(self) -> None:
        cards = [VocabularyCard("飲む", "のむ", "喝", "水を飲む。", "I drink.", "2026-02-01")]
        with patch("src.server.api.notion_client.list_vocabulary_cards", return_value=cards):
            response = TestClient(app).get("/card")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [{
            "word": "飲む",
            "reading": "のむ",
            "meaning": "喝",
            "example": "水を飲む。",
            "translation": "I drink.",
            "created_time": "2026-02-01",
        }])

    def test_translate_delegates_to_service(self) -> None:
        result = MagicMock(
            translation="I drink.",
            japanese_with_furigana="飲む（のむ）",
            structure_anchor="主語 + 動詞",
            words_lemmatized=[],
        )
        with patch("src.server.api.translate_text", return_value=result) as translate_text:
            response = TestClient(app).post("/translate", json={"text": "飲む"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["translation"], "I drink.")
        translate_text.assert_called_once_with("飲む")


if __name__ == "__main__":
    unittest.main()