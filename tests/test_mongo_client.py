import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from pymongo.errors import DuplicateKeyError

from src.server.anki_export import AnkiWord
from src.server.mongo_client import MongoVocabularyClient


class MongoVocabularyClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.word = AnkiWord("食べた", "食べる", "たべる", "吃", "動詞")
        self.collection = MagicMock()
        self.database = MagicMock()
        self.database.__getitem__.return_value = self.collection
        self.mongo = MagicMock()
        self.mongo.__getitem__.return_value = self.database
        self.client = MongoVocabularyClient("mongodb://localhost", mongo_client=self.mongo)

    def test_inserts_word_and_creates_unique_compound_index(self) -> None:
        result = self.client.save_word(self.word)

        self.assertEqual(result.status, "added")
        self.collection.create_index.assert_called_once_with(
            [("Word", 1), ("Reading", 1)],
            unique=True,
            name="unique_word_reading",
            partialFilterExpression={
                "Word": {"$type": "string"},
                "Reading": {"$type": "string"},
            },
        )
        document = self.collection.insert_one.call_args.args[0]
        self.assertEqual(document["Word"], "食べる")
        self.assertEqual(document["Reading"], "たべる")
        self.assertEqual(document["Meaning"], "吃")
        self.assertEqual(document["Example"], "動詞")
        self.assertEqual(document["Translation"], "")
        self.assertIsInstance(document["created_at"], datetime)
        self.assertIsNotNone(document["created_at"].tzinfo)

    def test_returns_exists_for_duplicate_word(self) -> None:
        self.collection.insert_one.side_effect = DuplicateKeyError("duplicate")

        result = self.client.save_word(self.word)

        self.assertEqual(result.status, "exists")

    def test_reads_legacy_created_date_when_created_at_is_null(self) -> None:
        card = self.client._card_from_document(
            {"created_at": None, "Created Date": "September 12, 2026 6:44 AM"}
        )

        self.assertEqual(card.created_time, "September 12, 2026 6:44 AM")

    def test_lists_cards_newest_first_with_limit_and_offset(self) -> None:
        cursor = MagicMock()
        cursor.sort.return_value = cursor
        cursor.skip.return_value = cursor
        cursor.limit.return_value = cursor
        cursor.__iter__.return_value = iter([
            {
                "Word": "飲む",
                "Reading": "のむ",
                "Meaning": "喝",
                "Example": "水を飲む。",
                "Translation": "I drink.",
                "created_at": datetime(2026, 2, 1, tzinfo=timezone.utc),
            }
        ])
        self.collection.find.return_value = cursor

        cards = self.client.list_vocabulary_cards(limit=5, offset=10)

        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0].word, "飲む")
        self.assertEqual(cards[0].reading, "のむ")
        self.assertEqual(cards[0].meaning, "喝")
        self.assertEqual(cards[0].created_time, "2026-02-01T00:00:00.000Z")
        cursor.sort.assert_called_once_with([("created_at", -1), ("_id", -1)])
        cursor.skip.assert_called_once_with(10)
        cursor.limit.assert_called_once_with(5)

    def test_zero_limit_does_not_query(self) -> None:
        self.assertEqual(self.client.list_vocabulary_cards(limit=0), [])
        self.collection.find.assert_not_called()

    def test_save_without_uri_is_disabled(self) -> None:
        client = MongoVocabularyClient(uri="")

        result = client.save_word(self.word)

        self.assertEqual(result.status, "disabled")

    def test_list_without_uri_raises_clear_error(self) -> None:
        client = MongoVocabularyClient(uri="")

        with self.assertRaisesRegex(RuntimeError, "MONGO_URI"):
            client.list_vocabulary_cards()


if __name__ == "__main__":
    unittest.main()