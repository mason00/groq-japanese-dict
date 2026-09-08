from __future__ import annotations

from collections.abc import Callable

import gradio as gr


MOBILE_UI_CSS = """
.gradio-container {
    max-width: 100% !important;
    padding: 0 !important;
    background: #ffffff !important;
}

.gradio-container > .contain {
    border: 0 !important;
    box-shadow: none !important;
    background: #ffffff !important;
}

#clipboard-input,
#translation-output {
    border: 1px solid var(--border-color-primary) !important;
    border-radius: 8px !important;
    background: var(--background-fill-primary) !important;
}

#clipboard-input {
    margin-bottom: 16px !important;
}

#clipboard-input textarea,
#translation-output textarea {
    border: 0 !important;
    box-shadow: none !important;
}

#translation-output textarea {
    line-height: 1.65 !important;
    max-height: calc(100vh - 120px) !important;
    overflow-y: auto !important;
    resize: none !important;
}
"""


CLIPBOARD_POLL_JS = """
function() {
    let lastClipboard = null;
    let pollInProgress = false;

    const readClipboard = async () => {
        if (typeof AndroidBridge !== "undefined") {
            try {
                return AndroidBridge.getClipboardText();
            } catch (error) {
                console.error("Android clipboard read failed:", error);
                return null;
            }
        }

        if (navigator.clipboard && navigator.clipboard.readText) {
            try {
                return await navigator.clipboard.readText();
            } catch (error) {
                return null;
            }
        }

        return null;
    };

    const pollClipboard = async () => {
        if (pollInProgress) {
            return;
        }
        pollInProgress = true;

        try {
            const clipboardText = await readClipboard();

            if (typeof clipboardText !== "string" || !clipboardText.trim() || clipboardText === lastClipboard) {
                return;
            }

            const input = document.querySelector("#clipboard-input textarea, #clipboard-input input");
            const submit = document.querySelector("#clipboard-input button");
            if (!input || !submit) {
                return;
            }

            lastClipboard = clipboardText;
            const valueSetter = Object.getOwnPropertyDescriptor(
                input instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype,
                "value"
            ).set;
            valueSetter.call(input, clipboardText);
            input.dispatchEvent(new Event("input", { bubbles: true }));
            input.dispatchEvent(new Event("change", { bubbles: true }));
            submit.click();
        } finally {
            pollInProgress = false;
        }
    };

    document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "visible") {
            pollClipboard();
        }
    });
    window.addEventListener("focus", pollClipboard);

    if (document.visibilityState === "visible") {
        pollClipboard();
    }
}
"""


SUBMIT_CLIPBOARD_JS = """
async function(currentText) {
    let clipboardText = null;

    if (typeof AndroidBridge !== "undefined") {
        try {
            clipboardText = AndroidBridge.getClipboardText();
        } catch (error) {
            console.error("Android clipboard read failed:", error);
        }
    } else if (navigator.clipboard && navigator.clipboard.readText) {
        try {
            clipboardText = await navigator.clipboard.readText();
        } catch (error) {
            console.error("Browser clipboard read failed:", error);
        }
    }

    if (typeof clipboardText !== "string" || !clipboardText.trim()) {
        return currentText;
    }

    const input = document.querySelector("#clipboard-input textarea, #clipboard-input input");
    if (input) {
        const valueSetter = Object.getOwnPropertyDescriptor(
            input instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype,
            "value"
        ).set;
        valueSetter.call(input, clipboardText);
        input.dispatchEvent(new Event("input", { bubbles: true }));
        input.dispatchEvent(new Event("change", { bubbles: true }));
    }
    return clipboardText;
}
"""


AUTO_RESIZE_OUTPUT_JS = """
function() {
    const resizeOutput = () => {
        const output = document.querySelector("#translation-output textarea");
        if (!output) {
            return;
        }

        output.style.height = "auto";
        const availableHeight = Math.max(
            160,
            window.innerHeight - output.getBoundingClientRect().top - 16
        );
        const nextHeight = Math.min(output.scrollHeight, availableHeight);
        output.style.height = `${nextHeight}px`;
        output.style.overflowY = output.scrollHeight > availableHeight ? "auto" : "hidden";
    };

    window.addEventListener("resize", resizeOutput);
    window.setInterval(resizeOutput, 250);
    resizeOutput();
}
"""


def create_demo(
    translate_fn: Callable[[str], object],
) -> gr.Blocks:
    def format_result(result: object) -> str:
        words_lemmatized = getattr(result, "words_lemmatized", [])
        formatted_words = "\n".join(
            f"{word.surface}（{word.reading}） -> {word.dictionary_form}"
            f"：{word.definition}；{word.grammar_note}"
            for word in words_lemmatized
        ) or "无"
        return (
            f"{result.japanese_with_furigana.strip()}\n\n"
            f"{result.translation.strip()}\n\n"
            f"【语法骨架】\n{result.structure_anchor.strip()}\n\n"
            f"【词汇拆解】\n{formatted_words}"
        )

    def translate_and_format(text: str) -> str:
        return format_result(translate_fn(text))

    with gr.Blocks(title="日文振假名翻译工具") as demo:
        text_input = gr.Textbox(
            show_label=False,
            placeholder="输入日文",
            lines=3,
            max_lines=8,
            elem_id="clipboard-input",
            submit_btn="🔍",
        )

        result_output = gr.Textbox(
            show_label=False,
            lines=8,
            max_lines=100,
            interactive=False,
            elem_id="translation-output",
        )
        text_input.submit(
            translate_and_format,
            text_input,
            result_output,
            js=SUBMIT_CLIPBOARD_JS,
        )
        demo.load(None, js=CLIPBOARD_POLL_JS)
        demo.load(None, js=AUTO_RESIZE_OUTPUT_JS)
    return demo
