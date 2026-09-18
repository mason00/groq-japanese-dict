import unittest
from unittest.mock import MagicMock, patch

from src.server.anki_export import AnkiWord
from src.server.notion_client import NotionClient


class NotionClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.word = AnkiWord("食べた", "食べる", "たべる", "吃", "動詞")
        self.client = NotionClient("token", "database")

    @patch("src.server.notion_client.httpx.post")
    def test_skips_existing_word(self, post: MagicMock) -> None:
        query_response = MagicMock()
        query_response.json.return_value = {"results": [{"id": "page-id"}]}
        post.return_value = query_response

        result = self.client.save_word(self.word)

        self.assertEqual(result.status, "exists")
        self.assertEqual(post.call_count, 1)

    @patch("src.server.notion_client.httpx.post")
    def test_creates_word_when_not_found(self, post: MagicMock) -> None:
        query_response = MagicMock()
        query_response.json.return_value = {"results": []}
        create_response = MagicMock()
        post.side_effect = [query_response, create_response]

        result = self.client.save_word(self.word)

        self.assertEqual(result.status, "added")
        payload = post.call_args_list[1].kwargs["json"]
        self.assertEqual(payload["properties"]["Word"]["title"][0]["text"]["content"], "食べる")
        self.assertEqual(payload["properties"]["Meaning"]["rich_text"][0]["text"]["content"], "吃")
        self.assertEqual(payload["properties"]["Example"]["rich_text"][0]["text"]["content"], "動詞")
        self.assertEqual(payload["properties"]["Translation"]["rich_text"][0]["text"]["content"], "")
        self.assertNotIn("Type", payload["properties"])

    @patch("src.server.notion_client.httpx.post")
    def test_lists_vocabulary_cards_newest_first_across_pages(self, post: MagicMock) -> None:
        first_response = MagicMock()
        first_response.json.return_value = {
            "results": [
                {
                    "created_time": "2026-01-01T00:00:00.000Z",
                    "properties": {
                        "Word": {"title": [{"plain_text": "食べる"}]},
                        "Reading": {"rich_text": [{"plain_text": "たべる"}]},
                        "Meaning": {"rich_text": [{"plain_text": "吃"}]},
                        "Example": {"rich_text": [{"plain_text": "食べます。"}]},
                        "Translation": {"rich_text": [{"plain_text": "I eat."}]},
                    },
                }
            ],
            "has_more": True,
            "next_cursor": "next-page",
        }
        second_response = MagicMock()
        second_response.json.return_value = {
            "results": [
                {
                    "created_time": "2026-02-01T00:00:00.000Z",
                    "properties": {
                        "Word": {"title": [{"plain_text": "飲む"}]},
                        "Reading": {"rich_text": [{"plain_text": "のむ"}]},
                        "Meaning": {"rich_text": [{"plain_text": "喝"}]},
                        "Example": {"rich_text": []},
                        "Translation": {"rich_text": [{"plain_text": "I drink."}]},
                    },
                }
            ],
            "has_more": False,
        }
        post.side_effect = [first_response, second_response]

        cards = self.client.list_vocabulary_cards()

        self.assertEqual([card.word for card in cards], ["飲む", "食べる"])
        self.assertEqual(cards[0].reading, "のむ")
        self.assertEqual(cards[0].example, "")
        self.assertEqual(post.call_args_list[0].kwargs["json"], {"page_size": 100})
        self.assertEqual(
            post.call_args_list[1].kwargs["json"],
            {"page_size": 100, "start_cursor": "next-page"},
        )

    def test_lists_vocabulary_cards_requires_configuration(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "NOTION_TOKEN"):
            NotionClient().list_vocabulary_cards()


if __name__ == "__main__":
    unittest.main()