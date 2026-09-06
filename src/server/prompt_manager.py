from __future__ import annotations

from pathlib import Path


class PromptManager:
    def __init__(self, prompt_dir: Path | None = None) -> None:
        self.prompt_dir = prompt_dir or Path(__file__).parent / "prompts"

    def get_system_prompt(self, text: str = "") -> str:
        prompt_path = self.prompt_dir / "translation.txt"
        if not prompt_path.is_file():
            raise ValueError(f"提示词文件不存在: {prompt_path}")
        return prompt_path.read_text(encoding="utf-8").strip()