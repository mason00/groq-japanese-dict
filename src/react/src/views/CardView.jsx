import { useEffect, useRef, useState } from "react";
import { request } from "../lib/api";

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

export default function CardView() {
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

  const goHome = () => {
    window.history.pushState(null, "", "/");
    window.dispatchEvent(new PopStateEvent("popstate"));
  };

  return (
    <main className="workspace cards-workspace">
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
            <button type="button" onClick={() => move(-1)} disabled={num <= 1 || status.type === "loading"}>← 上一张</button>
            <button
              type="button"
              onClick={goHome}
              aria-label="回到首页"
              title="回到首页"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M3 10.5 12 3l9 7.5" />
                <path d="M5 9.5V20h14V9.5" />
                <path d="M10 20v-6h4v6" />
              </svg>
            </button>
            <button type="button" onClick={() => move(1)} disabled={!hasNext || status.type === "loading"}>下一张 →</button>
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
