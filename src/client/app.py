from __future__ import annotations

from collections.abc import Callable

import gradio as gr


CLIPBOARD_POLL_JS = """
function() {
    let lastClipboard = null;

    const pollClipboard = () => {
        if (typeof AndroidBridge === "undefined") {
            return;
        }

        let clipboardText;
        try {
            clipboardText = AndroidBridge.getClipboardText();
        } catch (error) {
            return;
        }

        if (typeof clipboardText !== "string" || !clipboardText.trim() || clipboardText === lastClipboard) {
            return;
        }

        const input = document.querySelector("#clipboard-input textarea, #clipboard-input input");
        const submit = document.querySelector("#clipboard-submit button, #clipboard-submit");
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
    };

    setInterval(pollClipboard, 2000);
    pollClipboard();
}
"""


def create_demo(
    translate_fn: Callable[[str], tuple[str, str, str, str]],
) -> gr.Interface:
    text_input = gr.Textbox(label="输入日文", elem_id="clipboard-input")
    demo = gr.Interface(
        fn=translate_fn,
        inputs=text_input,
        outputs=[
            gr.Textbox(label="AI 返回的振假名日语"),
            gr.Textbox(label="分词单词列表"),
            gr.Textbox(label="中文翻译"),
            gr.Textbox(label="N4 以上难词翻译"),
        ],
        title="日文振假名翻译工具",
        submit_btn=gr.Button("Submit", elem_id="clipboard-submit"),
    )
    with demo:
        demo.load(None, js=CLIPBOARD_POLL_JS)
    return demo
