from __future__ import annotations

from typing import Any

from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langsmith import traceable
from pydantic import BaseModel, Field, ValidationError, field_validator

from .llm_client import LLMClient
from .prompt_manager import PromptManager


class LemmatizedWord(BaseModel):
    surface: str = Field(min_length=1)
    dictionary_form: str = Field(min_length=1)
    reading: str = Field(min_length=1)
    definition: str = Field(min_length=1)
    grammar_note: str = Field(min_length=1)


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

        return evaluate_output(
            source, result.japanese_with_furigana, result.translation
        )

    def _build_chain(self) -> Any:
        """Build: input -> PromptTemplate -> LLM -> Pydantic parse."""
        return (
            RunnablePassthrough.assign(
                system_prompt=RunnableLambda(
                    lambda data: self._format_prompt(data["text"])
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

    def _format_prompt(self, text: str) -> str:
        prompt = self._prompt_manager.get_system_prompt(text)
        # Prompt files contain JSON braces; escape them before PromptTemplate parses them.
        template = prompt.replace("{", "{{").replace("}", "}}")
        return PromptTemplate.from_template(
            f"{template}\n\n用户输入的日文：{{text}}"
        ).format(text=text)

    @staticmethod
    def _parse_translation(content: str) -> TranslationResponse:
        try:
            result = TranslationResponse.parse_raw(content)
            return result.model_copy(
                update={
                    "translation": result.translation.strip(),
                    "japanese_with_furigana": result.japanese_with_furigana.strip(),
                    "structure_anchor": result.structure_anchor.strip(),
                }
            )
        except (ValidationError, ValueError) as error:
            raise LLMOutputError("LLM 必须返回包含非空 translation 字段的 JSON") from error