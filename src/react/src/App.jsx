import React from "react";
import { useEffect, useState } from "react";

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

  async function translate(event) {
    event.preventDefault();
    const value = text.trim();
    if (!value) {
      setStatus({ type: "error", message: "请输入日文后再翻译。" });
      return;
    }
    setStatus({ type: "loading", message: "正在分析句子..." });
    try {
      setResult(await request("/translate", { method: "POST", body: JSON.stringify({ text: value }) }));
      setStatus({ type: "success", message: "翻译完成" });
    } catch (error) {
      setStatus({ type: "error", message: error.message });
    }
  }

  return (
    <main className="workspace">
      <SectionHeading eyebrow="Japanese study desk" title="把一句日文，拆成可以理解的形状。">
        <span className="api-chip">API · /translate</span>
      </SectionHeading>
      <form className="translate-form" onSubmit={translate}>
        <label htmlFor="japanese-input">日文原句</label>
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
        </div>
        {status.message && <p className={`status ${status.type}`}>{status.message}</p>}
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
              {result.words_lemmatized.map((word) => (
                <article className="word-row" key={`${word.surface}-${word.dictionary_form}`}>
                  <strong>{word.surface}</strong>
                  <span>{word.reading}</span>
                  <div>
                    <b>{word.dictionary_form}</b>
                    <p>{word.definition}</p>
                  </div>
                  <small>{word.grammar_note}</small>
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

function CardView() {
  const [cards, setCards] = useState([]);
  const [index, setIndex] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [status, setStatus] = useState({ type: "loading", message: "正在读取词汇库..." });

  useEffect(() => {
    let active = true;
    request("/card")
      .then((data) => {
        if (!active) return;
        setCards(data);
        setStatus({ type: data.length ? "success" : "empty", message: data.length ? "" : "Notion 词汇库为空。" });
      })
      .catch((error) => active && setStatus({ type: "error", message: error.message }));
    return () => { active = false; };
  }, []);

  const card = cards[index];
  const move = (offset) => {
    setIndex((current) => Math.min(Math.max(current + offset, 0), cards.length - 1));
    setRevealed(false);
  };

  return (
    <main className="workspace cards-workspace">
      <SectionHeading eyebrow="Vocabulary library" title="让记过的词，再见一次。">
        <span className="api-chip">API · /card</span>
      </SectionHeading>
      {card ? (
        <section className={`flashcard ${revealed ? "is-revealed" : ""}`}>
          <div className="card-meta"><span>词汇卡</span><span>{index + 1} / {cards.length}</span></div>
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
            <button onClick={() => move(-1)} disabled={index === 0}>← 上一张</button>
            <button onClick={() => move(1)} disabled={index === cards.length - 1}>下一张 →</button>
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
  const [view, setView] = useState("translate");
  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" onClick={(event) => { event.preventDefault(); setView("translate"); }}>
          <span className="brand-seal">日</span>
          <span>日文振假名<em>学习工具</em></span>
        </a>
        <nav className="view-switcher" aria-label="主要视图">
          <button className={view === "translate" ? "active" : ""} onClick={() => setView("translate")}>翻译工作台</button>
          <button className={view === "cards" ? "active" : ""} onClick={() => setView("cards")}>词汇卡</button>
        </nav>
        <span className="connection-dot" title="React client">●</span>
      </header>
      {view === "translate" ? <TranslateView /> : <CardView />}
      <footer>日常一点，理解就会留下来。 <span>JAPANESE / CHINESE</span></footer>
    </div>
  );
}
