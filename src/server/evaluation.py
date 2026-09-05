from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

from langsmith import traceable


RUBY_PATTERN = re.compile(r"(?P<kanji>[一-龯々]+)（(?P<reading>[ぁ-ゖー]+)）")
KANJI_PATTERN = re.compile(r"[一-龯々]")


def furigana_correctness(source: str, generated: str) -> float:
    """Score ruby structure and preservation of non-ruby source characters."""
    matches = list(RUBY_PATTERN.finditer(generated))
    if not matches:
        return 0.0

    ruby_ok = all(match.group("kanji") and match.group("reading") for match in matches)
    source_kanji = set(KANJI_PATTERN.findall(source))
    generated_kanji = set(KANJI_PATTERN.findall(generated))
    coverage = len(source_kanji & generated_kanji) / max(1, len(source_kanji))
    return round((1.0 if ruby_ok else 0.0) * coverage, 3)


def translation_accuracy(candidate: str, reference: str | None = None) -> float | None:
    """Return similarity only when a human/reference translation is supplied."""
    if not reference:
        return None
    candidate = "".join(candidate.split())
    reference = "".join(reference.split())
    if not reference:
        return None
    return round(SequenceMatcher(None, candidate, reference).ratio(), 3)


def hallucination_check(source: str, generated_japanese: str, translation: str) -> float:
    """Heuristic risk score: preserved Japanese plus bounded translation expansion."""
    source_chars = {char for char in source if not char.isspace()}
    generated_chars = {char for char in generated_japanese if not char.isspace()}
    preserved = len(source_chars & generated_chars) / max(1, len(source_chars))
    expansion = len(translation) / max(1, len(source) * 4)
    return round(
        max(0.0, min(1.0, preserved * (1.0 - max(0.0, expansion - 1.0)))), 3
    )


@traceable(name="evaluate_translation", run_type="chain")
def evaluate_output(
    source: str,
    japanese_with_furigana: str,
    translation: str,
    reference_translation: str | None = None,
) -> dict[str, Any]:
    return {
        "furigana_correctness": furigana_correctness(source, japanese_with_furigana),
        "translation_accuracy": translation_accuracy(translation, reference_translation),
        "hallucination_score": hallucination_check(
            source, japanese_with_furigana, translation
        ),
    }