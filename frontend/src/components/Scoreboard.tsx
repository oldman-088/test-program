import { formatDuration, toArabicDigits } from "../game/logic";

interface ScoreboardProps {
  moves: number;
  attempts: number;
  matches: number;
  totalPairs: number;
  elapsedSeconds: number;
  bestStreak: number;
}

export function Scoreboard({
  moves,
  attempts,
  matches,
  totalPairs,
  elapsedSeconds,
  bestStreak,
}: ScoreboardProps) {
  return (
    <dl className="scoreboard" aria-label="نتائج الجولة">
      <div className="scoreboard__item">
        <dt>المحاولات</dt>
        <dd>{toArabicDigits(attempts)}</dd>
      </div>
      <div className="scoreboard__item">
        <dt>الوقت</dt>
        <dd dir="ltr">{formatDuration(elapsedSeconds)}</dd>
      </div>
      <div className="scoreboard__item">
        <dt>الأزواج</dt>
        <dd>
          {toArabicDigits(matches / 2)} / {toArabicDigits(totalPairs)}
        </dd>
      </div>
      <div className="scoreboard__item">
        <dt>أفضل تتابع</dt>
        <dd>{toArabicDigits(bestStreak)}</dd>
      </div>
      <div className="scoreboard__item scoreboard__item--muted">
        <dt>الحركات</dt>
        <dd>{toArabicDigits(moves)}</dd>
      </div>
    </dl>
  );
}
