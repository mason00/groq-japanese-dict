import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from src.server.api import app
from src.server.notion_client import VocabularyCard


class ApiTests(unittest.TestCase):
    def test_card_returns_vocabulary_cards(self) -> None:
        cards = [VocabularyCard("飲む", "のむ", "喝", "水を飲む。", "I drink.", "2026-02-01")]
        with patch("src.server.api.notion_client.list_vocabulary_cards", return_value=cards) as list_mock:
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
        list_mock.assert_called_once_with(limit=None)

    def test_card_supports_bare_number_query_param(self) -> None:
        cards = [VocabularyCard("飲む", "のむ", "喝", "水を飲む。", "I drink.", "2026-02-01")]
        with patch("src.server.api.notion_client.list_vocabulary_cards", return_value=cards) as list_mock:
            response = TestClient(app).get("/card?1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["word"], "飲む")
        list_mock.assert_called_once_with(limit=1)

    def test_card_supports_limit_query_param(self) -> None:
        cards = [VocabularyCard("飲む", "のむ", "喝", "水を飲む。", "I drink.", "2026-02-01")]
        with patch("src.server.api.notion_client.list_vocabulary_cards", return_value=cards) as list_mock:
            response = TestClient(app).get("/card?limit=5")

        self.assertEqual(response.status_code, 200)
        list_mock.assert_called_once_with(limit=5)

    def test_card_supports_count_query_param(self) -> None:
        cards = [VocabularyCard("飲む", "のむ", "喝", "水を飲む。", "I drink.", "2026-02-01")]
        with patch("src.server.api.notion_client.list_vocabulary_cards", return_value=cards) as list_mock:
            response = TestClient(app).get("/card?count=2")

        self.assertEqual(response.status_code, 200)
        list_mock.assert_called_once_with(limit=2)

    def test_card_supports_offset_query_param(self) -> None:
        cards = [VocabularyCard("食べる", "たべる", "吃", "", "eat", "2026-02-02")]
        with patch("src.server.api.notion_client.list_vocabulary_cards", return_value=cards) as list_mock:
            response = TestClient(app).get("/card?offset=20&limit=10")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["word"], "食べる")
        list_mock.assert_called_once_with(limit=10, offset=20)

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