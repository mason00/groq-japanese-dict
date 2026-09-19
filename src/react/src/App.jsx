import { useEffect, useState } from "react";
import CardView from "./views/CardView";
import TranslateView from "./views/TranslateView";

// Minimal pathname-based router — no library needed.
function usePathname() {
  const [pathname, setPathname] = useState(() => window.location.pathname);

  useEffect(() => {
    const onPop = () => setPathname(window.location.pathname);
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  return pathname;
}

export default function App() {
  const pathname = usePathname();
  const isCards = pathname === "/card" || pathname === "/card/";

  return (
    <div className="app-shell">
      {isCards ? <CardView /> : <TranslateView />}
      <footer>日常一点，理解就会留下来。 <span>JAPANESE / CHINESE</span></footer>
    </div>
  );
}
