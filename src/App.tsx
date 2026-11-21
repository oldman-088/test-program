import { useEffect, useState, useCallback } from 'react';
import { RotateCcw, Clock, MousePointerClick, Layers } from 'lucide-react';
import { Difficulty, GameState } from './game/types';
import { createInitialGameState, flipCard, resolveTurn } from './game/logic';
import { getStrings } from './i18n/strings';
import { Card } from './components/Card';
import { EndScreen } from './components/EndScreen';

const DIFFICULTIES: Difficulty[] = ['easy', 'normal', 'hard'];

export function App() {
  const strings = getStrings('ar');
  const [difficulty, setDifficulty] = useState<Difficulty>('normal');
  const [gameState, setGameState] = useState<GameState>(() =>
    createInitialGameState('normal')
  );
  const [seconds, setSeconds] = useState(0);
  const [hasStarted, setHasStarted] = useState(false);

  const startNewGame = useCallback((nextDifficulty: Difficulty = difficulty) => {
    setDifficulty(nextDifficulty);
    setGameState(createInitialGameState(nextDifficulty));
    setSeconds(0);
    setHasStarted(false);
  }, [difficulty]);

  useEffect(() => {
    if (!hasStarted || gameState.isCompleted) {
      return;
    }
    const interval = window.setInterval(() => {
      setSeconds((prev) => prev + 1);
    }, 1000);
    return () => window.clearInterval(interval);
  }, [hasStarted, gameState.isCompleted]);

  useEffect(() => {
    if (gameState.flippedIds.length !== 2) {
      return;
    }

    const [firstId, secondId] = gameState.flippedIds;
    const first = gameState.cards.find((c) => c.id === firstId);
    const second = gameState.cards.find((c) => c.id === secondId);
    const isMatch = first && second && first.pairId === second.pairId;

    const timer = window.setTimeout(() => {
      setGameState((prev) => resolveTurn(prev));
    }, isMatch ? 350 : 750);

    return () => window.clearTimeout(timer);
  }, [gameState.flippedIds, gameState.cards]);

  const handleFlip = (cardId: string) => {
    if (!hasStarted) {
      setHasStarted(true);
    }
    setGameState((prev) => flipCard(prev, cardId));
  };

  const gridColsClass =
    difficulty === 'hard'
      ? 'grid-cols-4 sm:grid-cols-6 max-w-2xl'
      : 'grid-cols-4 max-w-lg';

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center px-4 py-6 sm:py-10">
      <header className="w-full max-w-2xl text-center space-y-2">
        <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
          {strings.title}
        </h1>
        <p className="text-sm text-slate-400">{strings.subtitle}</p>
      </header>

      {/* Controls: Difficulty & New Game */}
      <section
        aria-label={strings.difficultyLabel}
        className="mt-6 w-full max-w-2xl flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-800 bg-slate-900/70 p-3"
      >
        <div className="flex flex-wrap items-center gap-1.5">
          {DIFFICULTIES.map((level) => {
            const active = difficulty === level;
            return (
              <button
                key={level}
                type="button"
                onClick={() => startNewGame(level)}
                className={`rounded-xl px-3 py-1.5 text-xs sm:text-sm font-medium transition ${
                  active
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'bg-slate-800/80 text-slate-300 hover:bg-slate-800'
                }`}
              >
                {strings.difficulties[level]}
              </button>
            );
          })}
        </div>

        <button
          type="button"
          onClick={() => startNewGame(difficulty)}
          className="inline-flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-800 px-3.5 py-1.5 text-xs sm:text-sm font-medium text-slate-200 transition hover:bg-slate-700"
        >
          <RotateCcw className="h-4 w-4" />
          <span>{strings.actions.newGame}</span>
        </button>
      </section>

      {/* Stats Bar */}
      <section className="mt-4 w-full max-w-2xl grid grid-cols-3 gap-3">
        <div className="flex items-center justify-center gap-2 rounded-xl border border-slate-800 bg-slate-900/60 px-3 py-2.5">
          <MousePointerClick className="h-4 w-4 text-indigo-400 shrink-0" />
          <div className="text-xs sm:text-sm">
            <span className="text-slate-400 me-1">{strings.stats.attempts}:</span>
            <span className="font-bold text-white">{gameState.attempts}</span>
          </div>
        </div>

        <div className="flex items-center justify-center gap-2 rounded-xl border border-slate-800 bg-slate-900/60 px-3 py-2.5">
          <Clock className="h-4 w-4 text-emerald-400 shrink-0" />
          <div className="text-xs sm:text-sm">
            <span className="text-slate-400 me-1">{strings.stats.time}:</span>
            <span className="font-bold text-white">
              {seconds} {strings.stats.secondsUnit}
            </span>
          </div>
        </div>

        <div className="flex items-center justify-center gap-2 rounded-xl border border-slate-800 bg-slate-900/60 px-3 py-2.5">
          <Layers className="h-4 w-4 text-amber-400 shrink-0" />
          <div className="text-xs sm:text-sm">
            <span className="text-slate-400 me-1">{strings.stats.pairs}:</span>
            <span className="font-bold text-white">
              {gameState.matchedPairs}/{gameState.totalPairs}
            </span>
          </div>
        </div>
      </section>

      {/* Game Board */}
      <main className="mt-6 w-full flex justify-center">
        <div className={`grid w-full gap-2.5 sm:gap-3 ${gridColsClass}`}>
          {gameState.cards.map((card) => (
            <Card
              key={card.id}
              card={card}
              disabled={gameState.isLocked}
              onFlip={handleFlip}
              strings={strings}
            />
          ))}
        </div>
      </main>

      {gameState.isCompleted && (
        <EndScreen
          attempts={gameState.attempts}
          seconds={seconds}
          difficulty={difficulty}
          onPlayAgain={() => startNewGame(difficulty)}
          strings={strings}
        />
      )}
    </div>
  );
}

export default App;
