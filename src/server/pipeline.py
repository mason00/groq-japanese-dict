from typing import Any

from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langsmith import traceable
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from .llm_client import LLMClient
from .prompt_manager import PromptManager


class WordExplanation(BaseModel):
    surface: str = Field(min_length=1)
    reading: str = Field(min_length=1)
    definition: str = Field(min_length=1)
    dictionary_form: str = Field(min_length=1)

    class Config:
        extra = "forbid"


class RawLLMResponse(BaseModel):
    translation: str = Field(min_length=1)
    japanese_with_furigana: str = Field(min_length=1)
    structure_anchor: str = Field(min_length=1)
    word_explanations: list[WordExplanation] = Field(default_factory=list)

    @field_validator("translation", "japanese_with_furigana", "structure_anchor")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("字段不能只包含空白字符")
        return value.strip()


class LemmatizedWord(BaseModel):
    word: str = Field(min_length=1)
    reading: str = Field(min_length=1)
    meaning: str = Field(min_length=1)
    example: str = Field(default="")
    translation: str = Field(default="")
    surface: str | None = None
    dictionary_form: str | None = None
    definition: str | None = None
    grammar_note: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _sync_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "word" not in data and "dictionary_form" in data:
                data["word"] = data["dictionary_form"]
            if "dictionary_form" not in data and "word" in data:
                data["dictionary_form"] = data["word"]
            if "surface" not in data and "word" in data:
                data["surface"] = data["word"]
            if "meaning" not in data and "definition" in data:
                data["meaning"] = data["definition"]
            if "definition" not in data and "meaning" in data:
                data["definition"] = data["meaning"]
            if "example" not in data and "grammar_note" in data:
                data["example"] = data["grammar_note"]
            if "grammar_note" not in data and "example" in data:
                data["grammar_note"] = data["example"]
            if "translation" not in data:
                data["translation"] = ""
        return data


class TranslationResponse(BaseModel):
    translation: str = Field(min_length=1)
    japanese_with_furigana: str = Field(min_length=1)
    structure_anchor: str = Field(min_length=1)
    words_lemmatized: list[LemmatizedWord] = Field(default_factory=list)

    class Config:
        extra = "forbid"

    @field_validator("translation", "japanese_with_furigana", "structure_anchor")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("字段不能只包含空白字符")
        return value.strip()


class LLMOutputError(ValueError):
    pass


class JapanesePipeline:
    def __init__(self, llm_client: LLMClient, prompt_manager: PromptManager | None = None) -> None:
        self._llm_client = llm_client
        self._prompt_manager = prompt_manager or PromptManager()
        self._chain = self._build_chain()

    def process(self, text: str) -> TranslationResponse:
        try:
            output = self._chain.invoke({"text": text})
        except LLMOutputError as error:
            error_message = f"翻译格式错误：{error}"
            return TranslationResponse(
                translation=error_message,
                japanese_with_furigana=error_message,
                structure_anchor="无",
            )
        metrics = self._evaluate_output(text, output["result"])
        print(f"LangSmith evaluation: {metrics}", flush=True)
        return output["result"]

    @traceable(name="llm_translation", run_type="llm")
    def _invoke_llm(self, text: str, system_prompt: str):
        return self._llm_client.complete(text, system_prompt)

    @traceable(name="evaluate_current_output", run_type="chain")
    def _evaluate_output(self, source: str, result: TranslationResponse) -> dict[str, Any]:
        from .evaluation import evaluate_output

        return evaluate_output(source, result.japanese_with_furigana, result.translation)

    def _build_chain(self) -> Any:
        """Build: input -> prompts -> LLM -> response validation."""
        return (
            RunnablePassthrough.assign(
                system_prompt=RunnableLambda(lambda data: self._format_prompt()),
            )
            .assign(
                user_prompt=RunnableLambda(
                    lambda data: self._format_user_prompt(data["text"])
                ),
            )
            .assign(
                response=RunnableLambda(
                    lambda data: self._invoke_llm(
                        data["user_prompt"], data["system_prompt"]
                    )
                ),
            )
            .assign(
                result=RunnableLambda(
                    lambda data: self._merge_results(data["response"].content)
                ),
            )
        )

    def _format_prompt(self) -> str:
        return self._prompt_manager.get_system_prompt()

    def _format_user_prompt(self, text: str) -> str:
        return f"用户输入的日文：{text}"

    def _merge_results(self, content: str) -> TranslationResponse:
        try:
            raw = RawLLMResponse.model_validate_json(content)
        except (ValidationError, ValueError) as error:
            raise LLMOutputError(
                "LLM 必须返回包含 translation, japanese_with_furigana, structure_anchor, word_explanations 字段的合法 JSON"
            ) from error

        words_lemmatized = [
            LemmatizedWord(
                word=item.dictionary_form,
                reading=item.reading,
                meaning=item.definition,
                example=raw.japanese_with_furigana,
                translation=raw.translation,
                surface=item.surface,
                dictionary_form=item.dictionary_form,
                definition=item.definition,
            )
            for item in raw.word_explanations
        ]

        return TranslationResponse(
            translation=raw.translation,
            japanese_with_furigana=raw.japanese_with_furigana,
            structure_anchor=raw.structure_anchor,
            words_lemmatized=words_lemmatized,
        )
