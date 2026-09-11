from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4


ANKI_HEADER = "#separator:Tab\n#html:true\n#columns:Front\tBack\tTags\n"


@dataclass(frozen=True)
class AnkiWord:
    surface: str
    dictionary_form: str
    reading: str
    definition: str
    grammar_note: str

    @property
    def key(self) -> tuple[str, str]:
        return (self.dictionary_form.strip(), self.reading.strip())

    def to_tsv_row(self) -> str:
        front = f"{escape(self.dictionary_form)}（{escape(self.reading)}）"
        back = f"{escape(self.definition)}<br>{escape(self.grammar_note)}"
        return "\t".join(_clean_field(value) for value in (front, back, "japanese"))


def _clean_field(value: str) -> str:
    return " ".join(value.replace("\t", " ").replace("\r", " ").replace("\n", " ").split())


import os


class AnkiExportStore:
    """Stores each Gradio session's pending Anki cards as an importable TSV."""

    def __init__(self, root: Path | None = None) -> None:
        if root is not None:
            self._root = root
        elif os.path.isdir("/data"):
            self._root = Path("/data/groq-japanese-dict-anki")
        else:
            self._root = Path(gettempdir()) / "groq-japanese-dict-anki"

    def get_pending_count(self, session_id: str) -> int:
        try:
            path = self._path_for(session_id)
            if not path.exists():
                return 0
            return len(self._existing_keys(path))
        except Exception:
            return 0

    def add_word(self, session_id: str, word: AnkiWord) -> bool:
        path = self._path_for(session_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and word.key in self._existing_keys(path):
            return False

        is_new_file = not path.exists()
        with path.open("a", encoding="utf-8", newline="\n") as export_file:
            if is_new_file:
                export_file.write(ANKI_HEADER)
            export_file.write(f"{word.to_tsv_row()}\n")
        return True

    def export_and_clear(self, session_id: str) -> Path | None:
        path = self._path_for(session_id)
        if not path.exists() or path.stat().st_size <= len(ANKI_HEADER):
            return None

        export_path = path.with_name(f"anki-{session_id}-{uuid4().hex}.tsv")
        path.replace(export_path)
        return export_path

    def _path_for(self, session_id: str) -> Path:
        safe_session_id = "".join(
            char for char in session_id if char.isascii() and (char.isalnum() or char in "-_")
        )
        if not safe_session_id:
            raise ValueError("Invalid session identifier")
        return self._root / f"pending-{safe_session_id}.tsv"

    @staticmethod
    def _existing_keys(path: Path) -> set[tuple[str, str]]:
        keys: set[tuple[str, str]] = set()
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line or line.startswith("#"):
                continue
            front = line.split("\t", 1)[0]
            if "（" in front and front.endswith("）"):
                dictionary_form, reading = front[:-1].split("（", 1)
                keys.add((dictionary_form, reading))
        return keys
