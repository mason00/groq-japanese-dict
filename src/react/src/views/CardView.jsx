import { useEffect, useRef, useState } from "react";
import { request } from "../lib/api";

const CARD_WINDOW_SIZE = 20;
const PREFETCH_THRESHOLD = 5;

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
  const cardsCache = useRef(new Map());
  const windowRequests = useRef(new Map());
  const loadedWindows = useRef(new Set());
  const endIndex = useRef(null);

  const loadWindow = (windowStart) => {
    if (loadedWindows.current.has(windowStart)) return Promise.resolve(null);
    if (windowRequests.current.has(windowStart)) {
      return windowRequests.current.get(windowStart);
    }

    const requestPromise = request(`/card?offset=${windowStart}&limit=${CARD_WINDOW_SIZE}`)
      .then((data) => {
        if (!Array.isArray(data)) return [];

        loadedWindows.current.add(windowStart);
        data.forEach((item, index) => {
          cardsCache.current.set(windowStart + index + 1, item);
        });
        if (data.length < CARD_WINDOW_SIZE) {
          endIndex.current = windowStart + data.length;
        }
        return data;
      })
      .finally(() => {
        windowRequests.current.delete(windowStart);
      });

    windowRequests.current.set(windowStart, requestPromise);
    return requestPromise;
  };

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

    const revealTimer = window.setTimeout(() => {
      if (active) setRevealed(true);
    }, 5000);

    const windowStart = Math.floor((num - 1) / CARD_WINDOW_SIZE) * CARD_WINDOW_SIZE;
    const cachedCard = cardsCache.current.get(num);
    const windowPromise = cachedCard ? Promise.resolve([]) : loadWindow(windowStart);

    if (!cachedCard) {
      setStatus({ type: "loading", message: `正在读取第 ${num} 张词汇卡...` });
    }

    windowPromise
      .then((data) => {
        if (!active) return;
        const currentCard = cardsCache.current.get(num);
        if (!currentCard) {
          setCard(null);
          setHasNext(false);
          setStatus({ type: "empty", message: "Notion 词汇库为空。" });
          return;
        }

        setCard(currentCard);
        setHasNext(endIndex.current === null || num + 1 <= endIndex.current);
        setStatus({ type: "success", message: "" });

        const isNearWindowEnd = num >= windowStart + CARD_WINDOW_SIZE - PREFETCH_THRESHOLD;
        if (isNearWindowEnd && (endIndex.current === null || num + 1 <= endIndex.current)) {
          loadWindow(windowStart + CARD_WINDOW_SIZE).then((nextData) => {
            if (active && nextData && nextData.length === 0) setHasNext(false);
          }).catch(() => {
            // Keep the current card usable if background prefetch fails.
          });
        }
      })
      .catch((error) => {
        if (!active) return;
        setStatus({ type: "error", message: error.message });
      });

    return () => {
      active = false;
      window.clearTimeout(revealTimer);
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
        <section className={`flashcard ${revealed ? "is-revealed" : ""}`} onClick={() => setRevealed(true)}>
          <div className="card-meta"><span>词汇卡</span><span>第 {num} 张</span></div>
          <button className="card-word" aria-label="显示词汇卡详情">
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
