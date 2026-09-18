"""Browser-side assets used by the Gradio client."""


MOBILE_UI_CSS = """
#text-input,
#translation-output,
#words-table {
    padding: 0 !important;
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
            const submit = document.querySelector("#submit-button button, button#submit-button");
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
    const findButton = (id) => document.querySelector(`#${id} button, button#${id}`);

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

    if (document.documentElement.dataset.nativePasteBound === "true") return;
    document.documentElement.dataset.nativePasteBound = "true";
    document.addEventListener("click", async (event) => {
        if (!(event.target instanceof Element)) return;
        const clickedPaste = event.target.closest("#native-paste-button");
        const submitTrigger = () => findButton("submit-button")?.click();

        if (!clickedPaste) return;

        const clipboardText = await readClipboard();
        const input = document.querySelector("#clipboard-input textarea, #clipboard-input input");
        if (input && typeof clipboardText === "string" && clipboardText.trim()) setInputValue(input, clipboardText);
        requestAnimationFrame(submitTrigger);
    });
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


CARD_URL_SYNC_JS = """
function() {
    if (document.documentElement.dataset.cardUrlSyncBound === "true") return;
    const counter = document.querySelector("#card-counter");
    if (!counter) return;
    document.documentElement.dataset.cardUrlSyncBound = "true";

    const syncUrl = () => {
        const position = Number.parseInt(counter.textContent, 10);
        if (!Number.isInteger(position) || position < 1) return;
        const query = `?${position}`;
        if (window.location.search !== query) {
            window.history.replaceState(null, "", `${window.location.pathname}${query}${window.location.hash}`);
        }
    };

    new MutationObserver(syncUrl).observe(counter, { childList: true, characterData: true, subtree: true });
    syncUrl();
}
"""


CARD_UI_CSS = """
#card-title {
    text-align: center;
    margin-top: 2rem;
}

#vocabulary-card button {
    min-height: 16rem;
    white-space: normal;
    font-size: 2rem;
}

#card-details {
    min-height: 8rem;
    padding: 1rem;
    border: 1px solid var(--border-color-primary);
}

#card-counter {
    text-align: center;
}

#card-navigation {
    max-width: 32rem;
    margin: 0 auto;
}
"""