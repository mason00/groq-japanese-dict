from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


JLPTLevel = Literal["N1", "N2", "N3", "N4", "N5", "unknown"]
LEVEL_RANK = {"N1": 1, "N2": 2, "N3": 3, "N4": 4, "N5": 5}


class CandidateWord(BaseModel):
    word: str = Field(min_length=1)
    reading: str = ""
    part_of_speech: str = Field(min_length=1)
    jlpt_level: JLPTLevel = "unknown"


class WordDifficultyLexicon:
    def __init__(self, path: Path | None = None) -> None:
        default_path = Path(__file__).parent / "data" / "jlpt_levels.json"
        self.path = path or Path(os.getenv("JLPT_LEVELS_PATH", default_path))
        self._levels = self._load()

    def level_for(self, word: str) -> JLPTLevel:
        level = self._levels.get(word)
        return level if level in LEVEL_RANK or level == "unknown" else "unknown"

    def is_n4_or_harder(self, level: JLPTLevel) -> bool:
        return level == "unknown" or LEVEL_RANK.get(level, 99) <= 4

    def _load(self) -> dict[str, str]:
        if not self.path.is_file():
            return {}
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"JLPT 词表必须是 JSON 对象: {self.path}")
        return {str(word): str(level).upper() for word, level in data.items()}