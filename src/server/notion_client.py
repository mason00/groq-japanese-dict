from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

from src.server.anki_export import AnkiWord


NOTION_API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def _log(message: str) -> None:
    try:
        print(f"[notion] {message}", flush=True)
    except UnicodeEncodeError:
        safe_message = message.encode("ascii", errors="backslashreplace").decode("ascii")
        print(f"[notion] {safe_message}", flush=True)


@dataclass(frozen=True)
class NotionSaveResult:
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


class NotionClient:
    """Adds vocabulary to a Notion database without creating duplicates."""

    def __init__(
        self,
        token: str | None = None,
        database_id: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.token = token or os.getenv("NOTION_TOKEN", "").strip()
        self.database_id = database_id or os.getenv("NOTION_DATABASE_ID", "").strip()
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.token and self.database_id)

    def save_word(self, word: AnkiWord) -> NotionSaveResult:
        word_key = f"{word.dictionary_form.strip()}（{word.reading.strip()}）"
        _log(f"save started: {word_key}")
        if not self.configured:
            _log("save skipped: NOTION_TOKEN or NOTION_DATABASE_ID is not configured")
            return NotionSaveResult("disabled", "未配置 NOTION_TOKEN 或 NOTION_DATABASE_ID")

        if self._exists(word):
            _log(f"save skipped: already exists: {word_key}")
            return NotionSaveResult("exists")

        _log(f"creating page in database: {self.database_id}")
        try:
            response = httpx.post(
                f"{NOTION_API_URL}/pages",
                headers=self._headers(),
                json=self._page_payload(word),
                timeout=self.timeout,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            _log(
                f"create failed: status={error.response.status_code} "
                f"body={error.response.text[:500]}"
            )
            raise
        except Exception as error:
            _log(f"create failed: {type(error).__name__}: {error}")
            raise
        _log(f"create succeeded: {word_key}")
        return NotionSaveResult("added")

    def list_vocabulary_cards(self) -> list[VocabularyCard]:
        if not self.configured:
            raise RuntimeError("未配置 NOTION_TOKEN 或 NOTION_DATABASE_ID")

        cards: list[VocabularyCard] = []
        start_cursor: str | None = None
        while True:
            payload: dict[str, object] = {"page_size": 100}
            if start_cursor:
                payload["start_cursor"] = start_cursor
            response = httpx.post(
                f"{NOTION_API_URL}/databases/{self.database_id}/query",
                headers=self._headers(),
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            cards.extend(self._card_from_page(page) for page in data.get("results", []))
            if not data.get("has_more"):
                break
            start_cursor = data.get("next_cursor")
            if not start_cursor:
                break

        return sorted(cards, key=lambda card: card.created_time, reverse=True)

    def _exists(self, word: AnkiWord) -> bool:
        _log(
            f"query started: word={word.dictionary_form.strip()} "
            f"reading={word.reading.strip()} database={self.database_id}"
        )
        try:
            response = httpx.post(
                f"{NOTION_API_URL}/databases/{self.database_id}/query",
                headers=self._headers(),
                json={
                    "filter": {
                        "and": [
                            {"property": "Word", "title": {"equals": word.dictionary_form.strip()}},
                            {"property": "Reading", "rich_text": {"equals": word.reading.strip()}},
                        ]
                    },
                    "page_size": 1,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            exists = bool(response.json().get("results"))
        except httpx.HTTPStatusError as error:
            _log(
                f"query failed: status={error.response.status_code} "
                f"body={error.response.text[:500]}"
            )
            raise
        except Exception as error:
            _log(f"query failed: {type(error).__name__}: {error}")
            raise
        _log(f"query succeeded: exists={exists}")
        return exists

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        }

    @staticmethod
    def _card_from_page(page: dict[str, object]) -> VocabularyCard:
        properties = page.get("properties", {})
        if not isinstance(properties, dict):
            properties = {}
        return VocabularyCard(
            word=NotionClient._property_text(properties.get("Word"), "title"),
            reading=NotionClient._property_text(properties.get("Reading"), "rich_text"),
            meaning=NotionClient._property_text(properties.get("Meaning"), "rich_text"),
            example=NotionClient._property_text(properties.get("Example"), "rich_text"),
            translation=NotionClient._property_text(properties.get("Translation"), "rich_text"),
            created_time=str(page.get("created_time", "")),
        )

    @staticmethod
    def _property_text(property_value: object, property_type: str) -> str:
        if not isinstance(property_value, dict):
            return ""
        fragments = property_value.get(property_type, [])
        if not isinstance(fragments, list):
            return ""
        return "".join(
            fragment.get("plain_text", "")
            for fragment in fragments
            if isinstance(fragment, dict) and isinstance(fragment.get("plain_text"), str)
        )

    def _page_payload(self, word: AnkiWord) -> dict[str, object]:
        return {
            "parent": {"database_id": self.database_id},
            "properties": {
                "Word": {"title": [{"text": {"content": word.dictionary_form.strip()}}]},
                "Reading": {"rich_text": [{"text": {"content": word.reading.strip()}}]},
                "Meaning": {"rich_text": [{"text": {"content": word.definition.strip()}}]},
                "Example": {"rich_text": [{"text": {"content": word.grammar_note.strip()}}]},
                "Translation": {"rich_text": [{"text": {"content": word.translation.strip()}}]},
            },
        }