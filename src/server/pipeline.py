from __future__ import annotations

from typing import Any

from jamdict import Jamdict
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langsmith import traceable
from pydantic import BaseModel, Field, ValidationError, field_validator
from sudachipy import dictionary

from .llm_client import LLMClient
from .prompt_manager import PromptManager
from .word_difficulty import CandidateWord, WordDifficultyLexicon


def _to_hiragana(text: str) -> str:
    return "".join(
        chr(ord(char) - 0x60) if "ァ" <= char <= "ヺ" else char
        for char in text
    )


class WordTranslation(BaseModel):
    word: str = Field(min_length=1)
    translation: str = Field(min_length=1)


class TranslationResponse(BaseModel):
    translation: str = Field(min_length=1)
    japanese_with_furigana: str = Field(min_length=1)
    difficult_words: list[WordTranslation] = Field(default_factory=list)

    class Config:
        extra = "forbid"

    @field_validator("translation", "japanese_with_furigana")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("字段不能只包含空白字符")
        return value.strip()


class LLMOutputError(ValueError):
    pass


class JapanesePipeline:
    def __init__(self, llm_client: LLMClient, prompt_manager: PromptManager | None = None) -> None:
        self._tokenizer = dictionary.Dictionary().create()
        self._dictionary = Jamdict(reuse_ctx=False)
        self._llm_client = llm_client
        self._prompt_manager = prompt_manager or PromptManager()
        self._difficulty_lexicon = WordDifficultyLexicon()
        self._chain = self._build_chain()

    def process(self, text: str) -> tuple[str, str, str, str]:
        try:
            output = self._chain.invoke({"text": text})
        except LLMOutputError as error:
            error_message = f"翻译格式错误：{error}"
            return (
                error_message,
                self._format_word_lookups(text),
                error_message,
                self._format_llm_difficult_words(
                    [], self._unresolved_difficult_words(text)
                ),
            )
        metrics = self._evaluate_output(text, output["result"])
        print(f"LangSmith evaluation: {metrics}", flush=True)
        return (
            output["result"].japanese_with_furigana,
            self._format_word_lookups(text),
            output["result"].translation,
            self._format_llm_difficult_words(
                output["result"].difficult_words,
                output["unresolved_words"],
            ),
        )

    @traceable(name="llm_translation", run_type="llm")
    def _invoke_llm(self, text: str, system_prompt: str):
        return self._llm_client.complete(text, system_prompt)

    @traceable(name="evaluate_current_output", run_type="chain")
    def _evaluate_output(self, source: str, result: TranslationResponse) -> dict[str, Any]:
        from .evaluation import evaluate_output

        return evaluate_output(
            source, result.japanese_with_furigana, result.translation
        )

    def _build_chain(self) -> Any:
        """Build: input -> tokenize -> PromptTemplate -> LLM -> Pydantic parse."""
        return (
            RunnablePassthrough.assign(
                words=RunnableLambda(lambda data: self._tokenize(data["text"])),
            )
            .assign(
                unresolved_words=RunnableLambda(
                    lambda data: self._unresolved_difficult_words(data["text"])
                ),
            )
            .assign(
                system_prompt=RunnableLambda(
                    lambda data: self._format_prompt(
                        data["text"], data["unresolved_words"]
                    )
                ),
            )
            .assign(
                response=RunnableLambda(
                    lambda data: self._invoke_llm(
                        data["text"], data["system_prompt"]
                    )
                ),
            )
            .assign(
                result=RunnableLambda(
                    lambda data: self._parse_translation(data["response"].content)
                ),
            )
        )

    def _tokenize(self, text: str) -> str:
        return " / ".join(
            token.surface() for token in self._tokenizer.tokenize(text)
        )

    def _format_word_lookups(self, text: str) -> str:
        formatted_words = []
        for token in self._tokenizer.tokenize(text):
            surface = token.surface()
            dictionary_form = token.dictionary_form()
            glosses = self._lookup_glosses(dictionary_form)
            if not glosses:
                continue
            definition = "; ".join(glosses)
            formatted_words.append(f"{surface}（{dictionary_form}）: {definition}")
        return "\n\n".join(formatted_words) or "无"

    def _difficult_word_candidates(self, text: str) -> list[CandidateWord]:
        candidates = []
        allowed_pos = {"名詞", "動詞", "形容詞", "形容動詞"}
        seen = set()
        for token in self._tokenizer.tokenize(text):
            part_of_speech = token.part_of_speech()[0]
            word = token.dictionary_form()
            if part_of_speech not in allowed_pos or word in seen:
                continue
            level = self._difficulty_lexicon.level_for(word)
            if not self._difficulty_lexicon.is_n4_or_harder(level):
                continue
            seen.add(word)
            candidates.append(
                CandidateWord(
                    word=word,
                    reading=_to_hiragana(token.reading_form()),
                    part_of_speech=part_of_speech,
                    jlpt_level=level,
                )
            )
        return candidates

    def _format_prompt(
        self, text: str, unresolved_words: list[CandidateWord]
    ) -> str:
        prompt = self._prompt_manager.get_system_prompt(text)
        # Prompt files contain JSON braces; escape them before PromptTemplate parses them.
        template = prompt.replace("{", "{{").replace("}", "}}")
        candidate_json = [{"word": candidate.word} for candidate in unresolved_words]
        return PromptTemplate.from_template(
            f"{template}\n\n用户输入的日文：{{text}}\n待补充难词：{{candidates}}"
        ).format(text=text, candidates=candidate_json)

    def _unresolved_difficult_words(self, text: str) -> list[CandidateWord]:
        return [
            candidate
            for candidate in self._difficult_word_candidates(text)
            if not self._lookup_glosses(candidate.word)
        ]

    @staticmethod
    def _format_llm_difficult_words(
        words: list[WordTranslation], candidates: list[CandidateWord]
    ) -> str:
        if not words:
            return "无"
        candidate_by_word = {candidate.word: candidate for candidate in candidates}
        formatted_words = []
        for word in words:
            candidate = candidate_by_word.get(word.word)
            if candidate is None:
                continue
            formatted_words.append(
                f"{word.word}（{candidate.reading}）"
                f"{candidate.part_of_speech}: {word.translation}"
            )
        return "\n".join(formatted_words) or "无"

    def _format_local_difficult_words(self, candidates: list[CandidateWord]) -> str:
        if not candidates:
            return "无"
        formatted_words = []
        for candidate in candidates:
            definition = "; ".join(self._lookup_glosses(candidate.word)) or "无词条"
            formatted_words.append(
                f"{candidate.word}（{candidate.reading}）"
                f"{candidate.part_of_speech}: {definition}"
            )
        return "\n".join(formatted_words)

    def _lookup_glosses(self, word: str) -> list[str]:
        result = self._dictionary.lookup(word)
        glosses = []
        for entry in result.entries:
            for sense in entry.senses:
                if sense.gloss:
                    glosses.append(sense.gloss[0].text)
                if len(glosses) == 3:
                    return glosses
        return glosses

    @staticmethod
    def _parse_translation(content: str) -> TranslationResponse:
        try:
            result = TranslationResponse.parse_raw(content)
            return result.model_copy(
                update={
                    "translation": result.translation.strip(),
                    "japanese_with_furigana": result.japanese_with_furigana.strip(),
                }
            )
        except (ValidationError, ValueError) as error:
            raise LLMOutputError("LLM 必须返回包含非空 translation 字段的 JSON") from error