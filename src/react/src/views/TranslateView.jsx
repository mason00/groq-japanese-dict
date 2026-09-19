import { useEffect, useRef, useState } from "react";
import { request } from "../lib/api";

export default function TranslateView() {
  const [text, setText] = useState("");
  const [result, setResult] = useState(null);
  const [status, setStatus] = useState({ type: "idle", message: "" });
  const [autoPaste, setAutoPaste] = useState(true);
  const [saveResults, setSaveResults] = useState({});
  const [selectedWordKeys, setSelectedWordKeys] = useState({});

  const lastPastedTextRef = useRef("");
  const isTranslatingRef = useRef(false);

  async function doTranslate(rawText) {
    const value = (rawText || "").trim();
    if (!value) {
      setStatus({ type: "error", message: "请输入日文后再翻译。" });
      return;
    }
    lastPastedTextRef.current = value;
    isTranslatingRef.current = true;
    setStatus({ type: "loading", message: "正在分析句子..." });
    try {
      const data = await request("/translate", {
        method: "POST",
        body: JSON.stringify({ text: value }),
      });
      setResult(data);
      setStatus({ type: "success", message: "翻译完成" });
    } catch (error) {
      setStatus({ type: "error", message: error.message });
    } finally {
      isTranslatingRef.current = false;
    }
  }

  function translate(event) {
    event.preventDefault();
    doTranslate(text);
  }

  async function pasteAndTranslate() {
    if (!navigator?.clipboard?.readText) {
      setStatus({ type: "error", message: "当前浏览器或环境不支持直接读取剪切板。" });
      return;
    }
    try {
      const clipboardText = await navigator.clipboard.readText();
      const value = (clipboardText || "").trim();
      if (!value) {
        setStatus({ type: "error", message: "剪切板内容为空。" });
        return;
      }
      if (value === text) {
        return;
      }
      const hasJapanese = /[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]/.test(value);
      if (!hasJapanese) {
        return;
      }
      setText(value);
      await doTranslate(value);
    } catch {
      setStatus({ type: "error", message: "无法读取剪切板，请检查浏览器剪切板权限。" });
    }
  }

  function goToCards() {
    window.history.pushState(null, "", "/card");
    window.dispatchEvent(new PopStateEvent("popstate"));
  }

  async function handleSaveWord(word, idx) {
    const key = `${word.surface}-${idx}`;
    setSelectedWordKeys((prev) => ({ ...prev, [key]: true }));
    try {
      const response = await request("/save_word", {
        method: "POST",
        body: JSON.stringify({
          surface: word.surface,
          dictionary_form: word.dictionary_form,
          reading: word.reading,
          definition: word.meaning || word.definition,
          grammar_note: word.example,
          translation: word.translation,
        }),
      });
      setSaveResults((prev) => ({ ...prev, [key]: response }));
    } catch (e) {
      setSaveResults((prev) => ({
        ...prev,
        [key]: { status: "error", message: e.message },
      }));
    }
  }

  useEffect(() => {
    if (!autoPaste) return;

    let active = true;
    const checkClipboardOnActive = async () => {
      if (!active || isTranslatingRef.current) return;
      if (document.visibilityState !== "visible") return;
      if (!navigator?.clipboard?.readText) return;

      try {
        const clipboardText = await navigator.clipboard.readText();
        const value = (clipboardText || "").trim();
        if (!value) return;
        if (value === lastPastedTextRef.current) return;
        if (value === text) return;

        const hasJapanese = /[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]/.test(value);
        if (!hasJapanese) return;
        if (!active) return;

        setText(value);
        await doTranslate(value);
      } catch {
        // Silently ignore background focus/permission rejections
      }
    };

    window.addEventListener("focus", checkClipboardOnActive);
    document.addEventListener("visibilitychange", checkClipboardOnActive);

    return () => {
      active = false;
      window.removeEventListener("focus", checkClipboardOnActive);
      document.removeEventListener("visibilitychange", checkClipboardOnActive);
    };
  }, [autoPaste, text]);

  return (
    <main className="workspace">
      <form className="translate-form" onSubmit={translate}>
        <div className="input-row">
          <input
            id="japanese-input"
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder="例如：昨日は駅で友達に会いました。"
            autoComplete="off"
          />
          <button
            className="icon-button primary-icon-button"
            type="submit"
            disabled={status.type === "loading"}
            title={status.type === "loading" ? "处理中…" : "翻译"}
          >
            {status.type === "loading" ? (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
                <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
              </svg>
            ) : (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="5" y1="12" x2="19" y2="12"/>
                <polyline points="12 5 19 12 12 19"/>
              </svg>
            )}
          </button>
          <button
            className="icon-button tertiary-icon-button"
            type="button"
            onClick={goToCards}
            title="查看词汇卡"
            aria-label="前往词汇卡页面"
          >
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M4 7.5A2.5 2.5 0 0 1 6.5 5h11A2.5 2.5 0 0 1 20 7.5v9A2.5 2.5 0 0 1 17.5 19h-11A2.5 2.5 0 0 1 4 16.5v-9Z"/>
              <path d="M8 9h8M8 13h5"/>
            </svg>
          </button>
          <button
            className="icon-button secondary-icon-button"
            type="button"
            onClick={pasteAndTranslate}
            disabled={status.type === "loading"}
            title="粘贴剪切板内容并翻译"
          >
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="9" y="2" width="6" height="4" rx="1"/>
              <path d="M8 4H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2h-2"/>
            </svg>
          </button>
        </div>
      </form>

      {result ? (
        <div className="translation-grid">
          <section className="result-panel feature-panel">
            <div className="panel-label">译文</div>
            <p className="furigana">{result.japanese_with_furigana}</p>
            <p className="translation">{result.translation}</p>
            <div className="structure">
              <span>语法骨架</span>
              <p>{result.structure_anchor}</p>
            </div>
          </section>
          <section className="result-panel words-panel">
            <div className="panel-label">
              词汇拆解 <span>{result.words_lemmatized.length} 个词条</span>
            </div>
            <div className="word-list">
              {result.words_lemmatized.map((word, idx) => {
                const wordKey = `${word.surface}-${idx}`;
                return (
                <article
                  className={`word-row${selectedWordKeys[wordKey] ? " selected" : ""}`}
                  key={wordKey}
                  onClick={() => handleSaveWord(word, idx)}
                >
                  <strong>{word.surface}</strong>
                  <span>{word.reading}</span>
                  <div>
                    <b>{word.dictionary_form}</b>
                  </div>
                  <small>{word.definition}</small>
                  {saveResults[wordKey] && (
                    <p className="save-result">
                      {saveResults[wordKey].status}
                      {saveResults[wordKey].message
                        ? `: ${saveResults[wordKey].message}`
                        : ""}
                    </p>
                  )}
                </article>
                );
              })}
              {!result.words_lemmatized.length && <p className="empty-copy">这句话没有可拆解的词条。</p>}
            </div>
          </section>
        </div>
      ) : (
        <div className="empty-state">
          <span className="empty-mark">文</span>
          <p>输入一段日文，开始你的下一次阅读。</p>
        </div>
      )}
    </main>
  );
}
