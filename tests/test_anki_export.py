from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.server.anki_export import AnkiExportStore, AnkiWord


class AnkiExportStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.store = AnkiExportStore(Path(self.temporary_directory.name))
        self.word = AnkiWord("食べた", "食べる", "たべる", "吃", "动词")

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_adds_an_anki_tsv_card(self) -> None:
        self.assertTrue(self.store.add_word("session-1", self.word))
        export_path = self.store.export_and_clear("session-1")
        self.assertIsNotNone(export_path)
        contents = export_path.read_text(encoding="utf-8")
        self.assertIn("#separator:Tab", contents)
        self.assertIn("食べる（たべる）\t吃<br>动词\tjapanese", contents)

    def test_does_not_add_a_duplicate_dictionary_form_and_reading(self) -> None:
        self.assertTrue(self.store.add_word("session-1", self.word))
        self.assertFalse(self.store.add_word("session-1", self.word))

    def test_export_clears_the_pending_list(self) -> None:
        self.store.add_word("session-1", self.word)
        self.assertIsNotNone(self.store.export_and_clear("session-1"))
        self.assertIsNone(self.store.export_and_clear("session-1"))
