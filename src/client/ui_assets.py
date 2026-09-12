"""Browser-side assets used by the Gradio client."""


MOBILE_UI_CSS = """
.gradio-container {
    max-width: 100% !important;
    padding: 0 !important;
    background: #ffffff !important;
}

#native-paste-button,
#submit-button {
    margin-bottom: 0 !important;
}

#submit-trigger {
    display: none !important;
}

.gradio-container > .contain {
    border: 0 !important;
    box-shadow: none !important;
    background: #ffffff !important;
}

.no-padding {
    padding: 0 !important;
}
.no-padding .html-container {
    padding: 0 !important;
}

#clipboard-input,
#translation-output {
    border: 1px solid var(--border-color-primary) !important;
    border-radius: 8px !important;
    background: var(--background-fill-primary) !important;
    overflow: hidden !important;
    padding: 0 !important;
}

#clipboard-input .wrap,
#translation-output .wrap {
    border: 0 !important;
    box-shadow: none !important;
    background: transparent !important;
    padding: 0 !important;
}

#clipboard-input textarea,
#translation-output textarea {
    box-sizing: border-box !important;
    border: 0 !important;
    border-radius: 8px !important;
    box-shadow: none !important;
    background: transparent !important;
    padding: 14px !important;
}

#clipboard-input textarea {
    min-height: 56px !important;
}

#translation-output textarea {
    min-height: 180px !important;
    line-height: 1.65 !important;
    max-height: calc(100vh - 120px) !important;
    overflow-y: auto !important;
    resize: none !important;
}

#words-table table td.selected {
    background: transparent !important;
    outline: none !important;
}
#words-table table tr.selected td,
#words-table table tr:has(td.selected) td {
    background: var(--color-accent-soft, rgba(99, 102, 241, 0.15)) !important;
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
        if (pollInProgress) return;
        pollInProgress = true;
        try {
            const clipboardText = await readClipboard();
            if (typeof clipboardText !== "string" || !clipboardText.trim() || clipboardText === lastClipboard) return;
            const input = document.querySelector("#clipboard-input textarea, #clipboard-input input");
            const submit = document.querySelector("#clipboard-input button");
            if (!input || !submit) return;
            lastClipboard = clipboardText;
            const prototype = input instanceof HTMLTextAreaElement
                ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
            const valueSetter = Object.getOwnPropertyDescriptor(prototype, "value").set;
            valueSetter.call(input, clipboardText);
            input.dispatchEvent(new Event("input", { bubbles: true }));
            input.dispatchEvent(new Event("change", { bubbles: true }));
            submit.click();
        } finally {
            pollInProgress = false;
        }
    };

    document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "visible") pollClipboard();
    });
    window.addEventListener("focus", pollClipboard);
    if (document.visibilityState === "visible") pollClipboard();
}
"""


NATIVE_PASTE_BUTTON_JS = """
function() {
    const pasteBtn = document.querySelector("#native-paste-button");
    const submitBtn = document.querySelector("#submit-button");
    const gradioTrigger = document.querySelector("#submit-trigger button") || document.querySelector("button#submit-trigger");

    const setInputValue = (input, value) => {
        const prototype = input instanceof HTMLTextAreaElement
            ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
        const valueSetter = Object.getOwnPropertyDescriptor(prototype, "value").set;
        valueSetter.call(input, value);
        input.dispatchEvent(new Event("input", { bubbles: true }));
        input.dispatchEvent(new Event("change", { bubbles: true }));
    };

    const readClipboard = async () => {
        if (typeof AndroidBridge !== "undefined" && typeof AndroidBridge.getClipboardText === "function") {
            try { return AndroidBridge.getClipboardText(); }
            catch (error) { console.error("Android clipboard read failed:", error); }
        } else if (navigator.clipboard && navigator.clipboard.readText) {
            try { return await navigator.clipboard.readText(); }
            catch (error) { console.warn("Clipboard access blocked or denied:", error); }
        }
        return null;
    };

    if (submitBtn && !submitBtn.dataset.bound) {
        submitBtn.dataset.bound = "true";
        submitBtn.addEventListener("click", () => gradioTrigger?.click());
    }
    if (pasteBtn && !pasteBtn.dataset.bound) {
        pasteBtn.dataset.bound = "true";
        pasteBtn.addEventListener("click", async () => {
            const clipboardText = await readClipboard();
            const input = document.querySelector("#clipboard-input textarea, #clipboard-input input");
            if (input && typeof clipboardText === "string" && clipboardText.trim()) setInputValue(input, clipboardText);
            gradioTrigger?.click();
        });
    }
}
"""


AUTO_RESIZE_OUTPUT_JS = """
function() {
    const resizeOutput = () => {
        const output = document.querySelector("#translation-output textarea");
        if (!output) return;
        output.style.height = "auto";
        const availableHeight = Math.max(160, window.innerHeight - output.getBoundingClientRect().top - 16);
        const nextHeight = Math.min(output.scrollHeight, availableHeight);
        output.style.height = `${nextHeight}px`;
        output.style.overflowY = output.scrollHeight > availableHeight ? "auto" : "hidden";
    };
    window.addEventListener("resize", resizeOutput);
    window.setInterval(resizeOutput, 250);
    resizeOutput();
}
"""