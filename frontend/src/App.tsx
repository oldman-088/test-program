import { useState } from "react";
import { Board } from "./components/Board";
import { DifficultyPicker } from "./components/DifficultyPicker";
import { EndScreen } from "./components/EndScreen";
import { Leaderboard } from "./components/Leaderboard";
import { Scoreboard } from "./components/Scoreboard";
import { DIFFICULTIES, toArabicDigits } from "./game/logic";
import { useGame } from "./hooks/useGame";

export default function App() {
  const game = useGame();
  const config = DIFFICULTIES[game.difficulty];
  const [refreshKey, setRefreshKey] = useState(0);
  const [highlightId, setHighlightId] = useState<number | null>(null);

  const totalPairs = config.pairs;
  const locked = game.status === "won";

  function handleScoreSaved(id: number) {
    setHighlightId(id);
    setRefreshKey((key) => key + 1);
  }

  function handlePlayAgain() {
    game.restart();
  }

  function handleChangeDifficulty() {
    game.restart();
    document.getElementById("difficulty-heading")?.scrollIntoView({ behavior: "smooth" });
  }

  return (
    <div className="app">
      <header className="hero">
        <p className="hero__eyebrow">لعبة الذاكرة</p>
        <h1 className="hero__title">تطابق البطاقات</h1>
        <p className="hero__subtitle">
          اقلب البطاقات واعثر على الأزواج المتطابقة بأقل عدد من المحاولات وأسرع وقت.
        </p>
      </header>

      <main className="layout">
        <section className="panel game-panel" aria-labelledby="difficulty-heading">
          <h2 id="difficulty-heading" className="sr-only">
            إعدادات اللعبة
          </h2>

          <DifficultyPicker
            value={game.difficulty}
            onChange={game.changeDifficulty}
            disabled={game.status === "playing"}
          />

          <Scoreboard
            moves={game.board.moves}
            attempts={game.board.attempts}
            matches={game.board.matched.length}
            totalPairs={totalPairs}
            elapsedSeconds={game.elapsedSeconds}
            bestStreak={game.bestStreak}
          />

          <div className="game-panel__actions">
            <button
              type="button"
              className="button button--primary"
              onClick={game.status === "idle" ? game.start : game.restart}
            >
              {game.status === "idle" ? "ابدأ اللعب" : "إعادة التوزيع"}
            </button>
            <span className="game-panel__hint">
              {game.status === "idle"
                ? "اضغط على أي بطاقة للبدء — يبدأ المؤقّت فورًا."
                : `المستوى: ${config.label} • ${toArabicDigits(totalPairs)} أزواج`}
            </span>
          </div>

          <Board board={game.board} config={config} locked={locked} onFlip={game.flip} />
        </section>

        <aside className="layout__aside">
          <Leaderboard
            difficulty={game.difficulty}
            refreshKey={refreshKey}
            highlightId={highlightId}
          />
          <section className="panel tips" aria-labelledby="tips-heading">
            <h2 id="tips-heading" className="panel__title">
              نصائح سريعة
            </h2>
            <ul className="tips__list">
              <li>احفظ مواضع البطاقات التي قلبتها مؤخرًا.</li>
              <li>لا تتسرّع: الخطأ يكلّفك محاولة إضافية.</li>
              <li>التتابع المتتالي من المطابقات يرفع دقّتك.</li>
            </ul>
          </section>
        </aside>
      </main>

      {game.status === "won" && game.result && (
        <EndScreen
          result={game.result}
          onPlayAgain={handlePlayAgain}
          onChangeDifficulty={handleChangeDifficulty}
          onScoreSaved={handleScoreSaved}
        />
      )}

      <footer className="footer">
        <p>
          صُنعت بعناية — واجهة React بالعربية (RTL) وخلفية FastAPI لحفظ النتائج.
        </p>
      </footer>
    </div>
  );
}
