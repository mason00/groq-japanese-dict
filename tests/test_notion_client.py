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


if __name__ == "__main__":
    unittest.main()