from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from pymongo import ASCENDING, DESCENDING, MongoClient as PyMongoClient
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError

from src.server.anki_export import AnkiWord


MONGO_DATABASE = "japan-dict"
MONGO_COLLECTION = "vocab"


@dataclass(frozen=True)
class MongoSaveResult:
    status: str
    message: str = ""


@dataclass(frozen=True)
class VocabularyCard:
    word: str
    reading: str
    meaning: str
    example: str
    translation: str
    created_time: str


class MongoVocabularyClient:
    """Stores vocabulary cards in MongoDB without creating duplicates."""

    def __init__(
        self,
        uri: str | None = None,
        timeout: float = 10.0,
        mongo_client: Any | None = None,
    ) -> None:
        self.uri = (os.getenv("MONGO_URI", "") if uri is None else uri).strip()
        self.timeout = timeout
        self._client = mongo_client
        self._collection: Collection | None = None
        self._index_lock = Lock()
        self._index_created = False
        if self.configured and self._client is None:
            self._client = PyMongoClient(
                self.uri,
                serverSelectionTimeoutMS=int(timeout * 1000),
            )

    @property
    def configured(self) -> bool:
        return bool(self.uri)

    def save_word(self, word: AnkiWord) -> MongoSaveResult:
        if not self.configured:
            return MongoSaveResult("disabled", "未配置 MONGO_URI")

        collection = self._get_collection()
        self._ensure_unique_index(collection)
        document = {
            "Word": word.dictionary_form.strip(),
            "Reading": word.reading.strip(),
            "Meaning": word.definition.strip(),
            "Example": word.grammar_note.strip(),
            "Translation": word.translation.strip(),
            "created_at": datetime.now(timezone.utc),
        }
        try:
            collection.insert_one(document)
        except DuplicateKeyError:
            return MongoSaveResult("exists")
        return MongoSaveResult("added")

    def list_vocabulary_cards(
        self,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[VocabularyCard]:
        if not self.configured:
            raise RuntimeError("MONGO_URI is not configured")
        if limit is not None and limit <= 0:
            return []
        if offset < 0:
            raise ValueError("offset 不能小于 0")

        cursor = (
            self._get_collection()
            .find()
            .sort([("created_at", DESCENDING), ("_id", DESCENDING)])
            .skip(offset)
        )
        if limit is not None:
            cursor = cursor.limit(limit)
        return [self._card_from_document(document) for document in cursor]

    def _get_collection(self) -> Collection:
        if self._collection is None:
            self._collection = self._client[MONGO_DATABASE][MONGO_COLLECTION]
        return self._collection

    def _ensure_unique_index(self, collection: Collection) -> None:
        if self._index_created:
            return
        with self._index_lock:
            if self._index_created:
                return
            collection.create_index(
                [("Word", ASCENDING), ("Reading", ASCENDING)],
                unique=True,
                name="unique_word_reading",
                partialFilterExpression={
                    "Word": {"$type": "string"},
                    "Reading": {"$type": "string"},
                },
            )
            self._index_created = True

    @classmethod
    def _card_from_document(cls, document: dict[str, Any]) -> VocabularyCard:
        created_at = document.get("created_at")
        if created_at is None:
            created_at = document.get("Created Date", document.get("created_time"))
        return VocabularyCard(
            word=str(document.get("Word", document.get("word", ""))),
            reading=str(document.get("Reading", document.get("reading", ""))),
            meaning=str(document.get("Meaning", document.get("meaning", ""))),
            example=str(document.get("Example", document.get("example", ""))),
            translation=str(document.get("Translation", document.get("translation", ""))),
            created_time=cls._format_created_time(created_at),
        )

    @staticmethod
    def _format_created_time(value: object) -> str:
        if not isinstance(value, datetime):
            return str(value or "")
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace(
            "+00:00", "Z"
        )