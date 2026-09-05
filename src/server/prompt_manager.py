from __future__ import annotations

import hashlib
import os
from pathlib import Path


class PromptManager:
    def __init__(self, prompt_dir: Path | None = None) -> None:
        self.prompt_dir = prompt_dir or Path(__file__).parent / "prompts"
        self.mode = os.getenv("PROMPT_VERSION", "v1").lower()
        self.ab_split = min(100, max(0, int(os.getenv("PROMPT_AB_SPLIT", "50"))))

    def get_system_prompt(self, text: str) -> str:
        return self._read_prompt(self.version_for(text))

    def version_for(self, text: str) -> str:
        if self.mode == "ab":
            bucket = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16) % 100
            return "v1" if bucket < self.ab_split else "v2"
        return self.mode

    def _read_prompt(self, version: str) -> str:
        prompt_path = self.prompt_dir / f"translation_{version}.txt"
        if not prompt_path.is_file():
            available = sorted(
                path.stem.removeprefix("translation_")
                for path in self.prompt_dir.glob("translation_*.txt")
            )
            raise ValueError(
                f"提示词版本不存在: {version}，可用版本: {', '.join(available)}"
            )
        return prompt_path.read_text(encoding="utf-8").strip()