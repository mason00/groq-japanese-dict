from __future__ import annotations

from typing import Any

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
    difficult_words: list[WordTranslation]

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
        self._llm_client = llm_client
        self._prompt_manager = prompt_manager or PromptManager()
        self._difficulty_lexicon = WordDifficultyLexicon()
        self._chain = self._build_chain()

    def process(self, text: str) -> tuple[str, str, str, str]:
        try:
            output = self._chain.invoke({"text": text})
        except LLMOutputError as error:
            error_message = f"翻译格式错误：{error}"
            return error_message, self._tokenize(text), error_message, error_message
        metrics = self._evaluate_output(text, output["result"])
        print(f"LangSmith evaluation: {metrics}", flush=True)
        return (
            output["result"].japanese_with_furigana,
            output["words"],
            output["result"].translation,
            self._format_difficult_words(
                output["result"].difficult_words, output["difficult_words"]
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
                difficult_words=RunnableLambda(
                    lambda data: self._difficult_word_candidates(data["text"])
                ),
            )
            .assign(
                system_prompt=RunnableLambda(
                    lambda data: self._format_prompt(
                        data["text"], data["difficult_words"]
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

    def _format_prompt(self, text: str, difficult_words: list[CandidateWord]) -> str:
        prompt = self._prompt_manager.get_system_prompt(text)
        # Prompt files contain JSON braces; escape them before PromptTemplate parses them.
        template = prompt.replace("{", "{{").replace("}", "}}")
        candidate_json = [{"word": candidate.word} for candidate in difficult_words]
        return PromptTemplate.from_template(
            f"{template}\n\n用户输入的日文：{{text}}\n候选难词：{{candidates}}"
        ).format(text=text, candidates=candidate_json)

    @staticmethod
    def _format_difficult_words(
        words: list[WordTranslation], candidates: list[CandidateWord]
    ) -> str:
        if not words:
            return "无"
        candidate_by_word = {candidate.word: candidate for candidate in candidates}
        formatted_words = []
        for word in words:
            candidate = candidate_by_word.get(word.word)
            reading = candidate.reading if candidate else ""
            part_of_speech = candidate.part_of_speech if candidate else "unknown"
            formatted_words.append(
                f"{word.word}（{reading}）"
                f"{part_of_speech}: {word.translation}"
            )
        return "\n".join(formatted_words)

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