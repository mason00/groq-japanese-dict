from __future__ import annotations

import argparse
import unittest

from sudachipy import dictionary
from sudachipy.tokenizer import Tokenizer


EXAMPLE_SENTENCES = [
    "日本語を勉強します。",
    "昨日、東京で映画を見ました。",
    "食べられなかった理由を説明してください。",
    "この問題は思ったより難しいです。",
]


def create_tokenizer(mode: str = "C"):
    split_mode = getattr(Tokenizer.SplitMode, mode.upper())
    return dictionary.Dictionary().create(mode=split_mode)


def print_tokens(text: str, mode: str = "C") -> None:
    tokenizer = create_tokenizer(mode)
    tokens = tokenizer.tokenize(text)

    print(f"\n句子: {text}")
    print(f"模式: {mode.upper()}")
    print("表面形\t词典形\t读音\t词性")
    print("-" * 100)
    for token in tokens:
        print(
            f"{token.surface()}\t"
            f"{token.dictionary_form()}\t"
            f"{token.reading_form()}\t"
            f"{' / '.join(token.part_of_speech())}"
        )


class SudachiTokenizerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tokenizer = create_tokenizer()

    def test_token_surfaces_reconstruct_input(self) -> None:
        for sentence in EXAMPLE_SENTENCES:
            with self.subTest(sentence=sentence):
                tokens = self.tokenizer.tokenize(sentence)
                self.assertEqual("".join(token.surface() for token in tokens), sentence)

    def test_tokens_have_expected_metadata(self) -> None:
        tokens = self.tokenizer.tokenize(EXAMPLE_SENTENCES[0])

        self.assertGreater(len(tokens), 0)
        self.assertEqual(tokens[0].surface(), "日本語")
        self.assertEqual(tokens[0].dictionary_form(), "日本語")
        self.assertEqual(tokens[0].part_of_speech()[0], "名詞")

    def test_split_modes_can_be_compared(self) -> None:
        sentence = "食べられなかった"
        mode_a = create_tokenizer("A").tokenize(sentence)
        mode_c = create_tokenizer("C").tokenize(sentence)

        self.assertEqual("".join(token.surface() for token in mode_a), sentence)
        self.assertEqual("".join(token.surface() for token in mode_c), sentence)
        self.assertGreaterEqual(len(mode_a), len(mode_c))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="查看 SudachiPy 的分词和 token 属性")
    parser.add_argument(
        "sentences",
        nargs="*",
        help="要分析的日文句子；不传时使用内置示例",
    )
    parser.add_argument(
        "--mode",
        choices=("A", "B", "C"),
        default="C",
        help="SudachiPy 的切分模式，默认 C",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    for sentence in args.sentences or EXAMPLE_SENTENCES:
        print_tokens(sentence, args.mode)
    print("\n运行基础断言测试...")
    unittest.main(argv=[__file__], exit=False)