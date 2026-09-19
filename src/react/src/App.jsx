import React from "react";
import { useEffect, useRef, useState } from "react";

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.DEV ? "http://127.0.0.1:8000" : "")
).replace(/\/$/, "");

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!response.ok) {
    let message = `请求失败（${response.status}）`;
    try {
      const body = await response.json();
      message = body.detail || message;
    } catch {
      // Keep the HTTP status when the server does not return JSON.
    }
    throw new Error(message);
  }
  return response.json();
}

function SectionHeading({ eyebrow, title, children }) {
  return (
    <div className="section-heading">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
      </div>
      {children}
    </div>
  );
}

function TranslateView() {
  const [text, setText] = useState("");
  const [result, setResult] = useState(null);
  const [status, setStatus] = useState({ type: "idle", message: "" });
  const [autoPaste, setAutoPaste] = useState(true);
  const [saveResults, setSaveResults] = useState({});
  
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
      const data = await request("/translate", { method: "POST", body: JSON.stringify({ text: value }) });
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
      setText(value);
      await doTranslate(value);
    } catch (error) {
      setStatus({ type: "error", message: "无法读取剪切板，请检查浏览器剪切板权限。" });
    }
  }



  // Save a word to Notion via backend
  async function handleSaveWord(word, idx) {
    const key = `${word.word || word.surface}-${idx}`;
    try {
      const response = await request('/save_word', {
        method: 'POST',
        body: JSON.stringify({
          surface: word.surface || word.word,
          dictionary_form: word.dictionary_form,
          reading: word.reading,
          definition: word.meaning || word.definition,
          grammar_note: word.example,
          translation: word.translation,
        }),
      });
      setSaveResults(prev => ({ ...prev, [key]: response }));
    } catch (e) {
      setSaveResults(prev => ({
        ...prev,
        [key]: { status: 'error', message: e.message },
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
        // Skip if already processed this clipboard content
        if (value === lastPastedTextRef.current) return;
        // Skip if clipboard matches what's already in the input
        if (value === text) return;
        // Only auto-paste if content contains Japanese characters
        // (Hiragana U+3040–U+309F, Katakana U+30A0–U+30FF, Kanji U+4E00–U+9FFF)
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
          <button className="primary-button" type="submit" disabled={status.type === "loading"}>
            {status.type === "loading" ? "处理中" : "翻译"}
            <span aria-hidden="true">↗</span>
          </button>
          <button
            className="secondary-button"
            type="button"
            onClick={pasteAndTranslate}
            disabled={status.type === "loading"}
            title="粘贴剪切板内容并开始翻译"
          >
            粘贴并翻译
            <span aria-hidden="true">📋</span>
          </button>
        </div>
        <div className="form-options">
          <label className="auto-paste-toggle">
            <input
              type="checkbox"
              checked={autoPaste}
              onChange={(event) => setAutoPaste(event.target.checked)}
            />
            <span>窗口激活时自动粘贴翻译</span>
          </label>
          {status.message && <p className={`status ${status.type}`}>{status.message}</p>}
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
            <div className="panel-label">词汇拆解 <span>{result.words_lemmatized.length} 个词条</span></div>
            <div className="word-list">
              {result.words_lemmatized.map((word, idx) => (
                <article className="word-row" key={`${word.word || word.surface}-${idx}`} onClick={() => handleSaveWord(word, idx)}>
                  <strong>{word.word || word.surface}</strong>
                  <span>{word.reading}</span>
                  <div>
                    <b>{word.dictionary_form}</b>
                  </div>
                  <small>{word.grammar_note}</small>
                  {saveResults[`${word.word || word.surface}-${idx}`] && (
                    <p className="save-result">
                      {saveResults[`${word.word || word.surface}-${idx}`].status}
                      {saveResults[`${word.word || word.surface}-${idx}`].message
                        ? `: ${saveResults[`${word.word || word.surface}-${idx}`].message}`
                        : ""}
                    </p>
                  )}
                </article>
              ))}
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

function getInitialCardNum() {
  if (typeof window !== "undefined") {
    const search = window.location.search;
    const match = search.match(/^\?(\d+)/);
    if (match) {
      const parsed = parseInt(match[1], 10);
      if (parsed > 0) return parsed;
    }
    const params = new URLSearchParams(search);
    const cardVal = params.get("card") || params.get("limit") || params.get("page");
    if (cardVal && /^\d+$/.test(cardVal)) {
      const parsed = parseInt(cardVal, 10);
      if (parsed > 0) return parsed;
    }
  }
  return 1;
}

function CardView() {
  const [num, setNum] = useState(getInitialCardNum);
  const [card, setCard] = useState(null);
  const [revealed, setRevealed] = useState(false);
  const [hasNext, setHasNext] = useState(true);
  const [status, setStatus] = useState({ type: "loading", message: "正在读取词汇库..." });
  const cardsCache = useRef({});

  useEffect(() => {
    const onPopState = () => {
      setNum(getInitialCardNum());
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    let active = true;
    setRevealed(false);

    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.search = `?${num}`;
      window.history.replaceState(null, "", url.toString());
    }

    if (cardsCache.current[num]) {
      setCard(cardsCache.current[num]);
      setStatus({ type: "success", message: "" });
      return;
    }

    setStatus({ type: "loading", message: `正在读取第 ${num} 张词汇卡...` });
    request(`/card?${num}`)
      .then((data) => {
        if (!active) return;
        if (!Array.isArray(data) || data.length === 0) {
          setCard(null);
          setHasNext(false);
          setStatus({ type: "empty", message: "Notion 词汇库为空。" });
          return;
        }

        data.forEach((item, idx) => {
          cardsCache.current[idx + 1] = item;
        });

        if (data.length < num) {
          setCard(data[data.length - 1]);
          setNum(data.length);
          setHasNext(false);
          setStatus({ type: "success", message: "" });
          return;
        }

        setCard(data[num - 1]);
        setHasNext(true);
        setStatus({ type: "success", message: "" });
      })
      .catch((error) => {
        if (!active) return;
        setStatus({ type: "error", message: error.message });
      });

    return () => {
      active = false;
    };
  }, [num]);

  const move = (offset) => {
    const nextNum = Math.max(1, num + offset);
    if (nextNum === num) return;
    setRevealed(false);
    setNum(nextNum);
  };

  return (
    <main className="workspace cards-workspace">
      <SectionHeading eyebrow="Vocabulary library" title="让记过的词，再见一次。">
        <span className="api-chip">API · /card?{num}</span>
      </SectionHeading>
      {card ? (
        <section className={`flashcard ${revealed ? "is-revealed" : ""}`}>
          <div className="card-meta"><span>词汇卡</span><span>第 {num} 张</span></div>
          <button className="card-word" onClick={() => setRevealed(true)} aria-label="显示词汇卡详情">
            <span>{card.word}</span>
            {!revealed && <small>点击查看详情</small>}
          </button>
          <div className="card-details" aria-live="polite">
            {revealed ? (
              <div className="detail-grid">
                <div><span>读音</span><strong>{card.reading || "—"}</strong></div>
                <div><span>释义</span><strong>{card.meaning || "—"}</strong></div>
                <div><span>例句</span><strong>{card.example || "—"}</strong></div>
                <div><span>翻译</span><strong>{card.translation || "—"}</strong></div>
              </div>
            ) : <span className="card-hint">把答案留给自己几秒钟。</span>}
          </div>
          <div className="card-navigation">
            <button onClick={() => move(-1)} disabled={num <= 1 || status.type === "loading"}>← 上一张</button>
            <button onClick={() => move(1)} disabled={!hasNext || status.type === "loading"}>下一张 →</button>
          </div>
        </section>
      ) : (
        <div className={`empty-state card-empty ${status.type}`}>
          <span className="empty-mark">語</span>
          <p>{status.message}</p>
          {status.type === "error" && <small>请确认 API 地址和 Notion 配置。</small>}
        </div>
      )}
    </main>
  );
}

export default function App() {
  const [view, setView] = useState(() => {
    if (typeof window !== "undefined") {
      const search = window.location.search;
      if (/^\?(\d+|card|cards)/i.test(search)) {
        return "cards";
      }
    }
    return "translate";
  });

  return (
    <div className="app-shell">
      <header className="topbar">
        <a
          className="brand"
          href="/"
          onClick={(event) => {
            event.preventDefault();
            setView("translate");
            if (typeof window !== "undefined") {
              const url = new URL(window.location.href);
              url.search = "";
              window.history.replaceState(null, "", url.toString());
            }
          }}
        >
          <span className="brand-seal">日</span>
          <span>日文振假名<em>学习工具</em></span>
        </a>
        <nav className="view-switcher" aria-label="主要视图">
          <button
            className={view === "translate" ? "active" : ""}
            onClick={() => {
              setView("translate");
              if (typeof window !== "undefined") {
                const url = new URL(window.location.href);
                url.search = "";
                window.history.replaceState(null, "", url.toString());
              }
            }}
          >
            翻译工作台
          </button>
          <button
            className={view === "cards" ? "active" : ""}
            onClick={() => {
              setView("cards");
              if (typeof window !== "undefined" && !window.location.search) {
                const url = new URL(window.location.href);
                url.search = "?1";
                window.history.replaceState(null, "", url.toString());
              }
            }}
          >
            词汇卡
          </button>
        </nav>
        <span className="connection-dot" title="React client">●</span>
      </header>
      {view === "translate" ? <TranslateView /> : <CardView />}
      <footer>日常一点，理解就会留下来。 <span>JAPANESE / CHINESE</span></footer>
    </div>
  );
}
