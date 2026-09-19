from dataclasses import dataclass, field
from typing import Any

from jamdict import Jamdict
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langsmith import traceable
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator
from sudachipy import dictionary
from sudachipy.tokenizer import Tokenizer

from .llm_client import LLMClient
from .prompt_manager import PromptManager


TARGET_PARTS_OF_SPEECH = frozenset({"名詞", "動詞", "形容詞", "形状詞", "副詞"})
PUNCTUATION_POS = frozenset({"補助記号", "記号"})


def _to_hiragana(text: str) -> str:
    return "".join(
        chr(ord(char) - 0x60) if "ァ" <= char <= "ヺ" else char
        for char in text
    )


@dataclass
class LocalMorpheme:
    id: int
    surface: str
    dictionary_form: str
    reading: str
    pos: str
    glosses: list[str] = field(default_factory=list)


class WordExplanation(BaseModel):
    id: int
    definition: str = Field(min_length=1)
    grammar_note: str = Field(min_length=1)


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
        self._tokenizer = dictionary.Dictionary().create(mode=Tokenizer.SplitMode.C)
        self._dictionary = Jamdict(reuse_ctx=False)
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

    def _lookup_glosses(self, word: str) -> list[str]:
        try:
            result = self._dictionary.lookup(word)
        except Exception:
            return []
        glosses = []
        for entry in result.entries:
            for sense in entry.senses:
                if sense.gloss:
                    glosses.append(sense.gloss[0].text)
                if len(glosses) == 3:
                    return glosses
        return glosses

    def _extract_morphemes(self, text: str) -> tuple[list[LocalMorpheme], str]:
        tokens = self._tokenizer.tokenize(text)
        morphemes: list[LocalMorpheme] = []
        lines: list[str] = []
        current_id = 1

        for token in tokens:
            pos = token.part_of_speech()[0]
            if pos in PUNCTUATION_POS:
                continue
            surface = token.surface()
            dictionary_form = token.dictionary_form()
            reading = _to_hiragana(token.reading_form())
            glosses: list[str] = []

            if pos in TARGET_PARTS_OF_SPEECH:
                glosses = self._lookup_glosses(dictionary_form)
                gloss_str = "; ".join(glosses) if glosses else "无"
                lines.append(
                    f"{current_id}. 表面: {surface} | 原型: {dictionary_form} | 读音: {reading} | 词性: {pos} | JMdict英文参考: {gloss_str}"
                )
            else:
                lines.append(
                    f"{current_id}. 表面: {surface} | 原型: {dictionary_form} | 读音: {reading} | 词性: {pos}"
                )

            morphemes.append(
                LocalMorpheme(
                    id=current_id,
                    surface=surface,
                    dictionary_form=dictionary_form,
                    reading=reading,
                    pos=pos,
                    glosses=glosses,
                )
            )
            current_id += 1

        ref_text = "\n".join(lines) or "无"
        return morphemes, ref_text

    def _build_chain(self) -> Any:
        """Build: input -> morpheme extraction -> PromptTemplate -> LLM -> Local Merge."""
        return (
            RunnablePassthrough.assign(
                morphemes_data=RunnableLambda(
                    lambda data: self._extract_morphemes(data["text"])
                ),
            )
            .assign(
                system_prompt=RunnableLambda(
                    lambda data: self._format_prompt(
                        data["text"], data["morphemes_data"][1]
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
                    lambda data: self._merge_results(
                        data["response"].content, data["morphemes_data"][0]
                    )
                ),
            )
        )

    def _format_prompt(self, text: str, morphemes_ref: str) -> str:
        prompt = self._prompt_manager.get_system_prompt(text)
        # Prompt files contain JSON braces; escape them before PromptTemplate parses them.
        template = prompt.replace("{", "{{").replace("}", "}}")
        return PromptTemplate.from_template(
            f"{template}\n\n[本地词汇与JMdict参考]：\n{{morphemes_ref}}\n\n用户输入的日文：{{text}}"
        ).format(text=text, morphemes_ref=morphemes_ref)

    def _merge_results(
        self, content: str, local_morphemes: list[LocalMorpheme]
    ) -> TranslationResponse:
        try:
            raw = RawLLMResponse.model_validate_json(content)
        except (ValidationError, ValueError) as error:
            raise LLMOutputError(
                "LLM 必须返回包含 translation, japanese_with_furigana, structure_anchor, word_explanations 字段的合法 JSON"
            ) from error

        explanation_by_id = {item.id: item for item in raw.word_explanations}
        words_lemmatized: list[LemmatizedWord] = []

        for m in local_morphemes:
            exp = explanation_by_id.get(m.id)
            if exp and exp.definition.strip():
                definition = exp.definition.strip()
            elif m.glosses:
                definition = "; ".join(m.glosses)
            else:
                definition = "无"

            if exp and exp.grammar_note.strip():
                grammar_note = exp.grammar_note.strip()
            else:
                grammar_note = m.pos

            words_lemmatized.append(
                LemmatizedWord(
                    word=m.dictionary_form,
                    reading=m.reading,
                    meaning=definition,
                    example=raw.japanese_with_furigana.strip(),
                    translation=raw.translation.strip(),
                    surface=m.surface,
                    dictionary_form=m.dictionary_form,
                    definition=definition,
                    grammar_note=grammar_note,
                )
            )

        return TranslationResponse(
            translation=raw.translation.strip(),
            japanese_with_furigana=raw.japanese_with_furigana.strip(),
            structure_anchor=raw.structure_anchor.strip(),
            words_lemmatized=words_lemmatized,
        )